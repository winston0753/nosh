"""Suggestion session lifecycle: create, fetch, and respond."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contexts.models import DiningContext
from app.contexts.service import get_context_for_user
from app.contexts.validation import check_meal_window_key
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    InvalidStateError,
    NotFoundError,
    ValidationFailedError,
)
from app.places.models import Cuisine, Place, PlaceCuisine
from app.places.service import build_candidates
from app.recommendations.engine import recommend
from app.recommendations.priors import build_cuisine_stats
from app.recommendations.types import CuisineStats, NoCandidatesResult, RecommendationResult
from app.suggestions.models import Proposal, ProposalResponse, SuggestionSession
from app.suggestions.schemas import ProposalResponse_Schema

# Unique constraints on proposal_responses (migrations 0001 and 0003).
_CLIENT_EVENT_ID_CONSTRAINT = "proposal_responses_client_event_id_key"
_PROPOSAL_RESPONSE_CONSTRAINT = "uq_proposal_responses_proposal_id"


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
    dining_context_id: uuid.UUID,
    meal_window_key: str,
) -> SuggestionSession:
    """Idempotent: returns existing session or creates one.

    Concurrent-safe: locks the DiningContext row with SELECT FOR UPDATE before
    creating a new session.  This serialises simultaneous creation requests for
    the same (context, window) pair so exactly one session is ever inserted.

    The meal-window key must agree with the context: a real calendar date on
    one of its active days, its meal type, and a valid schedule (422
    ``validation_error`` otherwise).

    If no eligible candidates exist at creation time, sets state=no_candidates.
    """
    ctx = await get_context_for_user(db, dining_context_id, user_id)
    try:
        check_meal_window_key(
            meal_window_key,
            meal_type=ctx.meal_type,
            active_days=ctx.active_days,
            time_zone=ctx.time_zone,
            local_window_start=ctx.local_window_start,
            local_window_end=ctx.local_window_end,
        )
    except ValueError as exc:
        raise ValidationFailedError(str(exc), field="meal_window_key") from exc

    # Fast-path: read without a lock first.
    result = await db.execute(
        select(SuggestionSession)
        .where(
            SuggestionSession.dining_context_id == dining_context_id,
            SuggestionSession.meal_window_key == meal_window_key,
        )
        .options(selectinload(SuggestionSession.proposals).selectinload(Proposal.response))
    )
    session = result.scalar_one_or_none()
    if session is not None:
        if session.user_id != user_id:
            raise ForbiddenError()
        return session

    # Acquire a row-level lock on the context to serialise concurrent creation.
    await db.execute(
        select(DiningContext).where(DiningContext.id == dining_context_id).with_for_update()
    )

    # Re-check after acquiring the lock — a concurrent request may have created
    # the session between the unlocked read and the lock.
    result = await db.execute(
        select(SuggestionSession)
        .where(
            SuggestionSession.dining_context_id == dining_context_id,
            SuggestionSession.meal_window_key == meal_window_key,
        )
        .options(selectinload(SuggestionSession.proposals).selectinload(Proposal.response))
    )
    session = result.scalar_one_or_none()
    if session is not None:
        if session.user_id != user_id:
            raise ForbiddenError()
        return session

    # Create session; state starts active and may immediately become no_candidates.
    session = SuggestionSession(
        user_id=user_id,
        dining_context_id=dining_context_id,
        context_version=ctx.version,
        meal_window_key=meal_window_key,
        state="active",
        policy_version="policy_v0",
    )
    db.add(session)
    await db.flush()

    first = await _generate_next_proposal(db, session, ctx, user_id, already_proposed=set())
    if first is None:
        session.state = "no_candidates"
        session.closed_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(session)
    result = await db.execute(
        select(SuggestionSession)
        .where(SuggestionSession.id == session.id)
        .options(selectinload(SuggestionSession.proposals).selectinload(Proposal.response))
    )
    return result.scalar_one()


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
    """Record a Go/Another/Not today response.

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

    if response == "not_today":
        session.state = "skipped"
        session.closed_at = datetime.now(UTC)

    elif response == "go":
        session.state = "accepted"
        session.closed_at = datetime.now(UTC)

    elif response == "another":
        # The session row lock taken above also serialises concurrent Another
        # requests, so the proposal set read here cannot change underneath us.
        await db.refresh(session, attribute_names=["proposals"])
        ctx = await get_context_for_user(db, session.dining_context_id, user_id)
        already_proposed = {p.place_id for p in session.proposals}
        np = await _generate_next_proposal(db, session, ctx, user_id, already_proposed)
        if np is not None:
            next_proposal = await _proposal_to_schema(db, np)
        else:
            session.state = "exhausted"
            session.closed_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(session)
    return RecordedResponse(response=resp, session_state=session.state, next_proposal=next_proposal)


async def _generate_next_proposal(
    db: AsyncSession,
    session: SuggestionSession,
    ctx: DiningContext,
    user_id: uuid.UUID,
    already_proposed: set[uuid.UUID],
) -> Proposal | None:
    coord_result = await db.execute(
        select(
            func.ST_X(func.ST_GeomFromWKB(func.ST_AsBinary(DiningContext.location))).label("lon"),
            func.ST_Y(func.ST_GeomFromWKB(func.ST_AsBinary(DiningContext.location))).label("lat"),
        ).where(DiningContext.id == ctx.id)
    )
    coord_row = coord_result.one()
    lon, lat = float(coord_row.lon), float(coord_row.lat)

    candidates = await build_candidates(
        db,
        user_id,
        lon,
        lat,
        float(ctx.radius_meters),
        already_proposed,
    )
    stats_by_cuisine = await _load_cuisine_stats(db, user_id)
    sequence_number = len(already_proposed) + 1

    outcome = recommend(
        session_id=session.id,
        candidates=candidates,
        stats_by_cuisine=stats_by_cuisine,
        already_proposed=already_proposed,
        radius_meters=float(ctx.radius_meters),
        sequence_number=sequence_number,
        meal_type=ctx.meal_type,
    )

    if isinstance(outcome, NoCandidatesResult):
        return None

    assert isinstance(outcome, RecommendationResult)
    scored = outcome.proposal

    candidate_snapshot: dict[str, object] = {
        "candidate_count": outcome.candidate_count,
        "chosen_cuisine_slug": outcome.chosen_cuisine_slug,
        "cuisine_sample_used": outcome.cuisine_sample,
        "unvisited_pool_size": outcome.unvisited_pool_size,
        "exclusion_counts": outcome.exclusion_counts,
        "session_seed": outcome.session_seed,
        "distance_meters": scored.candidate.distance_meters,
    }

    proposal = Proposal(
        suggestion_session_id=session.id,
        place_id=scored.candidate.place_id,
        cuisine_id=scored.candidate.cuisine_id,
        sequence_number=sequence_number,
        total_score=scored.total_score,
        score_components=scored.score_components,
        reason_codes=scored.reason_codes,
        candidate_snapshot=candidate_snapshot,
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
        dining_context_id=session.dining_context_id,
        meal_window_key=session.meal_window_key,
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
    - Another → the proposal it generated, i.e. the next sequence number in the
      same session, with state ``active``; or ``exhausted`` when it generated
      none.  Only the latest proposal can be unanswered, so sequence + 1 is
      always the one this Another produced.
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
