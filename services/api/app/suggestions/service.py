"""Suggestion session lifecycle: create, fetch, and respond."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import (
    ConflictError,
    ForbiddenError,
    InvalidStateError,
    NoshError,
    NotFoundError,
    ValidationFailedError,
)
from app.places.models import Cuisine, Place, PlaceCuisine
from app.places.service import build_candidates, upsert_user_place_state
from app.recommendations.engine import POLICY_VERSION, recommend
from app.recommendations.priors import build_cuisine_stats
from app.recommendations.types import CuisineStats, RecommendationResult
from app.schedules.service import get_anchor_point, lock_meal_plan
from app.schedules.validation import check_meal_window_key, parse_meal_window_key
from app.suggestions.models import Proposal, ProposalResponse, SuggestionSession
from app.suggestions.schemas import ProposalResponse_Schema

# Unique constraints on proposal_responses (migrations 0001 and 0003).
_CLIENT_EVENT_ID_CONSTRAINT = "proposal_responses_client_event_id_key"
_PROPOSAL_RESPONSE_CONSTRAINT = "uq_proposal_responses_proposal_id"

# Candidates must be within walking range of the anchor.  policy_v1 (D024)
# replaces this fixed radius with walking time.
WALKING_RADIUS_METERS = 1600.0

# Responses that close the session, and those that advance to the next candidate.
_CLOSING = {"go": "accepted", "not_today": "skipped"}
_ADVANCING = ("another", "been_here")


@dataclass(frozen=True)
class RecordedResponse:
    """Result of recording (or replaying) a proposal response."""

    response: ProposalResponse
    session_state: str
    next_proposal: ProposalResponse_Schema | None

    @property
    def no_candidates(self) -> bool:
        return self.session_state == "exhausted"


async def get_or_create_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    meal_window_key: str,
    *,
    location: tuple[float, float] | None = None,
    anchor: str | None = None,
) -> SuggestionSession:
    """Idempotent: returns the user's session for the window, or creates it.

    ``location`` is the device's (longitude, latitude); ``anchor`` names a
    saved Home/Work spot.  Exactly one is given (enforced by the schema).  The
    coordinate is used once to rank candidates and is never stored or logged.

    Concurrent-safe: locks the user's meal_schedules row for the meal before
    creating, so simultaneous requests for one window insert exactly one
    session; the (user_id, meal_window_key) unique constraint backs this up.

    The key must name an enabled meal of the user's schedule, on one of its
    active days, with a valid stored schedule (422 ``validation_error``).  An
    unset anchor is 422 ``anchor_not_set``.  With no eligible candidates the
    session is created closed with state ``no_candidates``.
    """
    try:
        _, meal_type = parse_meal_window_key(meal_window_key)
    except ValueError as exc:
        raise ValidationFailedError(str(exc), field="meal_window_key") from exc

    # Fast path: read without a lock first.
    session = await _find_session(db, user_id, meal_window_key)
    if session is not None:
        return session

    plan = await lock_meal_plan(db, user_id, meal_type)
    if plan is None or not plan.enabled:
        raise ValidationFailedError(
            f"{meal_type} is not enabled in your meal schedule", field="meal_window_key"
        )
    try:
        check_meal_window_key(
            meal_window_key,
            meal_type=plan.meal_type,
            active_days=plan.active_days,
            time_zone=plan.time_zone,
            local_window_start=plan.local_window_start,
            local_window_end=plan.local_window_end,
        )
    except ValueError as exc:
        raise ValidationFailedError(str(exc), field="meal_window_key") from exc

    # Re-check under the lock: a concurrent request may have created it.
    session = await _find_session(db, user_id, meal_window_key)
    if session is not None:
        return session

    point: tuple[float, float] | None
    if location is not None:
        point, anchor_source = location, "device"
    else:
        assert anchor is not None
        point, anchor_source = await get_anchor_point(db, user_id, anchor), anchor
    if point is None:
        raise NoshError(
            code="anchor_not_set",
            message=f"No {anchor} spot is saved",
            status_code=422,
            field="anchor",
        )

    session = SuggestionSession(
        user_id=user_id,
        meal_window_key=meal_window_key,
        schedule_version=plan.version,
        anchor_source=anchor_source,
        state="active",
        policy_version=POLICY_VERSION,
        candidate_queue=[],
    )
    db.add(session)
    await db.flush()

    session.candidate_queue = await _rank_candidates(db, session, user_id, point, meal_type)
    if await _advance(db, session) is None:
        session.state = "no_candidates"
        session.closed_at = datetime.now(UTC)

    # Only the open meal window needs its queue; drop the user's older ones so
    # distances to unshown candidates are not retained.
    await db.execute(
        update(SuggestionSession)
        .where(
            SuggestionSession.user_id == user_id,
            SuggestionSession.id != session.id,
            SuggestionSession.candidate_queue != [],
        )
        .values(candidate_queue=[])
    )

    await db.commit()
    found = await _find_session(db, user_id, meal_window_key)
    assert found is not None
    return found


async def _find_session(
    db: AsyncSession, user_id: uuid.UUID, meal_window_key: str
) -> SuggestionSession | None:
    result = await db.execute(
        select(SuggestionSession)
        .where(
            SuggestionSession.user_id == user_id,
            SuggestionSession.meal_window_key == meal_window_key,
        )
        .options(selectinload(SuggestionSession.proposals).selectinload(Proposal.response))
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def get_session(
    db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> SuggestionSession:
    result = await db.execute(
        select(SuggestionSession)
        .where(SuggestionSession.id == session_id)
        .options(selectinload(SuggestionSession.proposals).selectinload(Proposal.response))
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise NotFoundError("session", str(session_id))
    if session.user_id != user_id:
        raise ForbiddenError()
    return session


async def record_response(
    db: AsyncSession,
    proposal_id: uuid.UUID,
    user_id: uuid.UUID,
    response: str,
    client_event_id: str,
) -> RecordedResponse:
    """Record a Go/Another/Not today/Been here already response.

    Idempotency and concurrency contract
    -------------------------------------
    same client_event_id + same proposal + same action  → return stored result
    same client_event_id + different proposal            → 409 ConflictError
    same client_event_id + different action              → 409 ConflictError
    proposal already answered with same action           → return stored result
    proposal already answered with different action      → 409 ConflictError
    concurrent conflicting actions on one proposal       → one wins, loser 409 ConflictError
    another user's response or event                     → 403 ForbiddenError
    unrelated database error                             → re-raised unchanged
    exactly one response row per proposal

    Session state corresponds to the single winning action.  Every replay
    returns a result equivalent to the original, including the next proposal
    that an Another produced (see ``_replay_outcome``).
    """
    # --- Fast-path: existing client_event_id ---
    existing = await db.execute(
        select(ProposalResponse).where(ProposalResponse.client_event_id == client_event_id)
    )
    existing_resp = existing.scalar_one_or_none()
    if existing_resp is not None:
        return await _replay_client_event(db, existing_resp, proposal_id, user_id, response)

    # --- Load proposal and verify ownership (unlocked) ---
    result = await db.execute(
        select(Proposal).where(Proposal.id == proposal_id).options(selectinload(Proposal.session))
    )
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise NotFoundError("proposal", str(proposal_id))
    if proposal.session.user_id != user_id:
        raise ForbiddenError()

    # --- Serialise responders on the session row ---
    # Every response to a proposal in this session takes this lock before
    # reading the stored response or the session state.  A concurrent loser
    # therefore blocks until the winner commits, then observes the winner's
    # response row and receives ConflictError — never InvalidStateError caused
    # by the winner's state change.  populate_existing discards stale state
    # from the unlocked read above.
    locked = await db.execute(
        select(SuggestionSession)
        .where(SuggestionSession.id == proposal.suggestion_session_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    session = locked.scalar_one()

    stored_result = await db.execute(
        select(ProposalResponse)
        .where(ProposalResponse.proposal_id == proposal_id)
        .execution_options(populate_existing=True)
    )
    stored = stored_result.scalar_one_or_none()
    if stored is not None:
        return await _resolve_answered_proposal(db, stored, user_id, response)

    if session.state != "active":
        raise InvalidStateError(f"Session is {session.state!r}, cannot respond")

    # --- Savepoint: add the new response inside protected scope ---
    # Opening the savepoint BEFORE db.add() prevents SQLAlchemy autoflush
    # from firing during begin_nested() and escaping the IntegrityError handler.
    nested = await db.begin_nested()
    try:
        resp = ProposalResponse(
            proposal_id=proposal_id,
            user_id=user_id,
            response=response,
            client_event_id=client_event_id,
            responded_at=datetime.now(UTC),
        )
        db.add(resp)
        await db.flush()
        await nested.commit()
    except IntegrityError as exc:
        # Roll back the savepoint so the outer session stays usable.
        await nested.rollback()

        # Only the two idempotency constraints are interpreted here.  Any
        # other IntegrityError (FK violation, etc.) is re-raised unchanged.
        detail = str(exc.orig)
        if _CLIENT_EVENT_ID_CONSTRAINT in detail:
            # The same client_event_id was committed concurrently, possibly
            # for a different proposal in another session.
            dup = await db.execute(
                select(ProposalResponse)
                .where(ProposalResponse.client_event_id == client_event_id)
                .execution_options(populate_existing=True)
            )
            dup_resp = dup.scalar_one_or_none()
            if dup_resp is not None:
                return await _replay_client_event(db, dup_resp, proposal_id, user_id, response)
        elif _PROPOSAL_RESPONSE_CONSTRAINT in detail:
            # Unreachable while all writers take the session lock above;
            # handled defensively so the contract holds regardless.
            winner = await db.execute(
                select(ProposalResponse)
                .where(ProposalResponse.proposal_id == proposal_id)
                .execution_options(populate_existing=True)
            )
            winner_resp = winner.scalar_one_or_none()
            if winner_resp is not None:
                return await _resolve_answered_proposal(db, winner_resp, user_id, response)
        raise

    next_proposal: ProposalResponse_Schema | None = None

    if response in _CLOSING:
        session.state = _CLOSING[response]
        session.closed_at = datetime.now(UTC)
        session.candidate_queue = []

    elif response in _ADVANCING:
        if response == "been_here":
            # D025: visited before Nosh.  Excluded from now on, feeds the
            # history prior, and never counts toward the North Star (D018).
            await upsert_user_place_state(
                db, user_id, proposal.place_id, "visited", "been_here", visited_before_nosh=True
            )
        # The session row lock taken above serialises concurrent responses,
        # so the queue read here cannot change underneath us.
        np = await _advance(db, session)
        if np is not None:
            next_proposal = await _proposal_to_schema(db, np)
        else:
            session.state = "exhausted"
            session.closed_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(session)
    return RecordedResponse(response=resp, session_state=session.state, next_proposal=next_proposal)


async def _rank_candidates(
    db: AsyncSession,
    session: SuggestionSession,
    user_id: uuid.UUID,
    point: tuple[float, float],
    meal_type: str,
) -> list[dict[str, object]]:
    """Rank every eligible candidate around ``point`` once, in proposal order.

    Entry *n* is exactly what policy_v0 would propose as sequence number *n*
    after the first *n - 1* entries were declined, so the order is the same as
    generating proposals one Another at a time.
    """
    lon, lat = point
    candidates = await build_candidates(db, user_id, lon, lat, WALKING_RADIUS_METERS, set())
    stats_by_cuisine = await _load_cuisine_stats(db, user_id)

    queue: list[dict[str, object]] = []
    proposed: set[uuid.UUID] = set()
    while True:
        outcome = recommend(
            session_id=session.id,
            candidates=candidates,
            stats_by_cuisine=stats_by_cuisine,
            already_proposed=proposed,
            radius_meters=WALKING_RADIUS_METERS,
            sequence_number=len(queue) + 1,
            meal_type=meal_type,
        )
        if not isinstance(outcome, RecommendationResult):
            return queue
        scored = outcome.proposal
        proposed.add(scored.candidate.place_id)
        queue.append(
            {
                "place_id": str(scored.candidate.place_id),
                "cuisine_id": str(scored.candidate.cuisine_id),
                "total_score": scored.total_score,
                "score_components": scored.score_components,
                "reason_codes": scored.reason_codes,
                "snapshot": {
                    "candidate_count": outcome.candidate_count,
                    "chosen_cuisine_slug": outcome.chosen_cuisine_slug,
                    "cuisine_sample_used": outcome.cuisine_sample,
                    "unvisited_pool_size": outcome.unvisited_pool_size,
                    "exclusion_counts": outcome.exclusion_counts,
                    "session_seed": outcome.session_seed,
                    "distance_meters": scored.candidate.distance_meters,
                },
            }
        )


async def _advance(db: AsyncSession, session: SuggestionSession) -> Proposal | None:
    """Turn the next queued candidate into a proposal, or return None if empty."""
    queue = list(session.candidate_queue)
    if not queue:
        return None
    entry = queue[0]
    # Reassign rather than mutate so SQLAlchemy sees the JSONB change.
    session.candidate_queue = queue[1:]

    count = await db.execute(
        select(Proposal.id).where(Proposal.suggestion_session_id == session.id)
    )
    proposal = Proposal(
        suggestion_session_id=session.id,
        place_id=uuid.UUID(str(entry["place_id"])),
        cuisine_id=uuid.UUID(str(entry["cuisine_id"])),
        sequence_number=len(count.all()) + 1,
        total_score=entry["total_score"],
        score_components=entry["score_components"],
        reason_codes=entry["reason_codes"],
        candidate_snapshot=entry["snapshot"],
    )
    db.add(proposal)
    await db.flush()
    return proposal


async def _load_cuisine_stats(
    db: AsyncSession, user_id: uuid.UUID
) -> dict[uuid.UUID, CuisineStats]:
    """Load per-cuisine evidence: pre-Nosh history plus confirmed proposal outcomes.

    History comes only from places flagged ``was_visited_before_nosh``; outcomes
    only from proposal-backed visits.  See ``app.recommendations.priors``.
    """
    from app.places.models import UserPlaceState
    from app.visits.models import Visit

    cuisines_result = await db.execute(select(Cuisine.id, Cuisine.slug))
    cuisine_slugs = {row.id: row.slug for row in cuisines_result.all()}

    history_result = await db.execute(
        select(PlaceCuisine.cuisine_id)
        .join(UserPlaceState, UserPlaceState.place_id == PlaceCuisine.place_id)
        .where(
            UserPlaceState.user_id == user_id,
            UserPlaceState.was_visited_before_nosh.is_(True),
            PlaceCuisine.is_primary.is_(True),
        )
    )
    pre_nosh_cuisine_ids = list(history_result.scalars().all())

    outcomes_result = await db.execute(
        select(PlaceCuisine.cuisine_id, Visit.rating)
        .join(PlaceCuisine, PlaceCuisine.place_id == Visit.place_id)
        .where(
            Visit.user_id == user_id,
            Visit.proposal_id.is_not(None),
            PlaceCuisine.is_primary.is_(True),
        )
    )
    proposal_outcomes = [(row.cuisine_id, row.rating) for row in outcomes_result.all()]

    return build_cuisine_stats(cuisine_slugs, pre_nosh_cuisine_ids, proposal_outcomes)


async def _proposal_to_schema(db: AsyncSession, proposal: Proposal) -> ProposalResponse_Schema:
    place_result = await db.execute(select(Place).where(Place.id == proposal.place_id))
    place = place_result.scalar_one()
    cuisine_result = await db.execute(select(Cuisine).where(Cuisine.id == proposal.cuisine_id))
    cuisine = cuisine_result.scalar_one_or_none()

    dist = float(proposal.candidate_snapshot.get("distance_meters", 0.0))  # type: ignore[arg-type]

    return ProposalResponse_Schema(
        id=proposal.id,
        place_id=proposal.place_id,
        place_name=place.canonical_name,
        cuisine_name=cuisine.display_name if cuisine else "",
        distance_meters=dist,
        address=place.address,
        reason_codes=proposal.reason_codes,
        sequence_number=proposal.sequence_number,
        total_score=proposal.total_score,
        score_components=proposal.score_components,
    )


async def session_to_response(db: AsyncSession, session: SuggestionSession) -> object:
    from app.suggestions.schemas import SessionResponse

    current_proposal = None
    if session.proposals:
        last = max(session.proposals, key=lambda p: p.sequence_number)
        if last.response is None and session.state == "active":
            current_proposal = await _proposal_to_schema(db, last)

    return SessionResponse(
        id=session.id,
        meal_window_key=session.meal_window_key,
        anchor_source=session.anchor_source,
        state=session.state,
        policy_version=session.policy_version,
        current_proposal=current_proposal,
        created_at=session.created_at,
    )


async def _replay_client_event(
    db: AsyncSession,
    existing: ProposalResponse,
    proposal_id: uuid.UUID,
    user_id: uuid.UUID,
    response: str,
) -> RecordedResponse:
    """Resolve a request whose client_event_id is already stored."""
    if existing.user_id != user_id:
        raise ForbiddenError()
    if existing.proposal_id != proposal_id:
        raise ConflictError("client_event_id already used for a different proposal")
    if existing.response != response:
        raise ConflictError("client_event_id already used for a different action")
    return await _replay_outcome(db, existing)


async def _resolve_answered_proposal(
    db: AsyncSession,
    stored: ProposalResponse,
    user_id: uuid.UUID,
    response: str,
) -> RecordedResponse:
    """Resolve a request for a proposal that already has a response."""
    if stored.user_id != user_id:
        raise ForbiddenError()
    if stored.response != response:
        raise ConflictError(
            f"A different action ({stored.response!r}) already recorded for this proposal"
        )
    return await _replay_outcome(db, stored)


async def _replay_outcome(db: AsyncSession, stored: ProposalResponse) -> RecordedResponse:
    """Reconstruct the result the original request returned.

    The session may have moved on since (e.g. Another followed by Go on the
    next proposal), so the result is derived from the stored response rather
    than the current session state:

    - Go → ``accepted``; Not today → ``skipped`` (closed sessions never change).
    - Another or Been here already → the proposal it generated, i.e. the next
      sequence number in the same session, with state ``active``; or
      ``exhausted`` when it generated none.  Only the latest proposal can be
      unanswered, so sequence + 1 is always the one this response produced.
    """
    if stored.response == "go":
        return RecordedResponse(response=stored, session_state="accepted", next_proposal=None)
    if stored.response == "not_today":
        return RecordedResponse(response=stored, session_state="skipped", next_proposal=None)

    answered = await db.get(Proposal, stored.proposal_id)
    assert answered is not None  # FK guarantees the proposal exists
    following = await db.execute(
        select(Proposal).where(
            Proposal.suggestion_session_id == answered.suggestion_session_id,
            Proposal.sequence_number == answered.sequence_number + 1,
        )
    )
    next_row = following.scalar_one_or_none()
    if next_row is None:
        return RecordedResponse(response=stored, session_state="exhausted", next_proposal=None)
    return RecordedResponse(
        response=stored,
        session_state="active",
        next_proposal=await _proposal_to_schema(db, next_row),
    )
