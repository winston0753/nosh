from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NoshError, NotFoundError
from app.places.models import Place, UserPlaceState
from app.visits.models import Visit
from app.visits.schemas import ProgressResponse, VisitCreate, VisitResponse, VisitUpdate


async def confirm_visit(db: AsyncSession, user_id: uuid.UUID, body: VisitCreate) -> VisitResponse:
    """Create a visit record.

    Proposal-backed visits (proposal_id is not None)
    ------------------------------------------------
    - Proposal must exist (404 if not).
    - Proposal session must belong to the requesting user (403).
    - There must be a ProposalResponse with response='go' for this exact
      proposal (422 if missing — prevents confirming 'Another'-rejected proposals
      or proposals from an accepted session that was accepted on a later proposal).
    - place_id must match the proposal's place_id (422).
    - Idempotency: duplicate confirmation for the same proposal returns the
      existing visit without error.
    - Concurrent retries: the (user_id, proposal_id) partial unique index
      (migration 0003) prevents races; IntegrityError is handled idempotently.

    Manual visits (proposal_id=None)
    ---------------------------------
    - No session-state or proposal validation.
    - Allowed per DECISIONS.md D015.
    - Do not count toward North Star unless the place was not visited before Nosh.
    """
    if body.proposal_id is not None:
        from app.suggestions.models import Proposal, ProposalResponse, SuggestionSession

        prop_result = await db.execute(select(Proposal).where(Proposal.id == body.proposal_id))
        proposal = prop_result.scalar_one_or_none()
        if proposal is None:
            raise NotFoundError("proposal", str(body.proposal_id))

        sess_result = await db.execute(
            select(SuggestionSession).where(SuggestionSession.id == proposal.suggestion_session_id)
        )
        session = sess_result.scalar_one_or_none()
        if session is None or session.user_id != user_id:
            raise ForbiddenError()

        # Require that the exact proposal was answered with 'go', not just that
        # the session is accepted (which could be true because a later proposal
        # received Go while earlier proposals received Another).
        go_result = await db.execute(
            select(ProposalResponse).where(
                ProposalResponse.proposal_id == body.proposal_id,
                ProposalResponse.response == "go",
            )
        )
        if go_result.scalar_one_or_none() is None:
            raise NoshError(
                code="proposal_not_accepted",
                message=(
                    "This proposal was not accepted with Go. "
                    "Only a Go response can be confirmed as a visit."
                ),
                status_code=422,
            )

        if proposal.place_id != body.place_id:
            raise NoshError(
                code="place_mismatch",
                message="place_id does not match the accepted proposal",
                status_code=422,
            )

        # Idempotency: return existing visit for this proposal.
        existing = await db.execute(
            select(Visit).where(
                Visit.user_id == user_id,
                Visit.proposal_id == body.proposal_id,
            )
        )
        row = existing.scalar_one_or_none()
        if row is not None:
            return await _to_response(db, row)

    visit = Visit(
        user_id=user_id,
        place_id=body.place_id,
        proposal_id=body.proposal_id,
        visited_at=body.visited_at,
        confirmation_source=body.confirmation_source,
        rating=body.rating,
    )
    db.add(visit)

    try:
        await db.flush()
    except IntegrityError as exc:
        # A concurrent request for the same (user_id, proposal_id) won the race.
        # Only interpret this as an idempotent duplicate when proposal_id is set
        # and the constraint name matches the expected partial unique index.
        # Any other IntegrityError (FK violation, etc.) is re-raised.
        constraint_hint = "uq_visits_user_proposal"
        if body.proposal_id is not None and constraint_hint in str(exc.orig):
            await db.rollback()
            existing = await db.execute(
                select(Visit).where(
                    Visit.user_id == user_id,
                    Visit.proposal_id == body.proposal_id,
                )
            )
            row = existing.scalar_one_or_none()
            if row is not None:
                return await _to_response(db, row)
        raise

    await _upsert_place_state(db, user_id, body.place_id, "visited", "confirmation")
    await db.commit()
    await db.refresh(visit)
    return await _to_response(db, visit)


async def update_visit(
    db: AsyncSession, user_id: uuid.UUID, visit_id: uuid.UUID, body: VisitUpdate
) -> VisitResponse:
    result = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = result.scalar_one_or_none()
    if visit is None:
        raise NotFoundError("visit", str(visit_id))
    if visit.user_id != user_id:
        raise ForbiddenError()

    if body.rating is not None:
        visit.rating = body.rating
    if body.visited_at is not None:
        visit.visited_at = body.visited_at
    visit.corrected_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(visit)
    return await _to_response(db, visit)


async def list_visits(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 50, cursor: uuid.UUID | None = None
) -> list[VisitResponse]:
    query = (
        select(Visit).where(Visit.user_id == user_id).order_by(Visit.visited_at.desc()).limit(limit)
    )
    if cursor is not None:
        cursor_result = await db.execute(
            select(Visit).where(Visit.id == cursor, Visit.user_id == user_id)
        )
        cursor_visit = cursor_result.scalar_one_or_none()
        if cursor_visit is None:
            raise NotFoundError("cursor visit", str(cursor))
        query = query.where(Visit.visited_at < cursor_visit.visited_at)

    result = await db.execute(query)
    return [await _to_response(db, v) for v in result.scalars().all()]


async def get_progress(db: AsyncSession, user_id: uuid.UUID) -> list[ProgressResponse]:
    """Monthly confirmed positive NEW-restaurant progress.

    A restaurant counts as 'new' only when was_visited_before_nosh is FALSE
    on its UserPlaceState row (set by migration 0004 backfill and by the
    onboarding flow).  This flag is never reset when a later confirmation
    updates the row, so provenance is preserved.

    A restaurant counts as 'new' at most once per user: the first confirmed
    positive Nosh visit in any month.
    """
    result = await db.execute(
        select(Visit).where(Visit.user_id == user_id).order_by(Visit.visited_at.asc())
    )
    all_visits = result.scalars().all()

    # Load pre-Nosh provenance once.
    pre_nosh_result = await db.execute(
        select(UserPlaceState.place_id).where(
            UserPlaceState.user_id == user_id,
            UserPlaceState.was_visited_before_nosh.is_(True),
        )
    )
    pre_nosh_places: set[uuid.UUID] = {row.place_id for row in pre_nosh_result.all()}

    return compute_progress_months(list(all_visits), pre_nosh_places)


def compute_progress_months(
    visits: list[Visit],
    pre_nosh_places: set[uuid.UUID],
) -> list[ProgressResponse]:
    """Pure computation of monthly progress from a list of visits.

    Extracted for testability.  Called by get_progress() after data fetching.

    Rules:
    - A place counts as 'new' at most once per user.
    - A 'pre-Nosh' place (was_visited_before_nosh=True) never counts as new.
    - Only positively rated visits increment positive_new.
    - Visits are processed in ascending time order so the first month of
      confirmed positive visit 'claims' the new-restaurant credit.
    """
    confirmed_in_nosh: set[uuid.UUID] = set()
    months: dict[str, dict[str, int]] = {}

    for visit in visits:
        month_key = visit.visited_at.strftime("%Y-%m")
        if month_key not in months:
            months[month_key] = {"positive_new": 0, "total": 0}

        months[month_key]["total"] += 1

        is_new = (
            visit.rating == "positive"
            and visit.place_id not in pre_nosh_places
            and visit.place_id not in confirmed_in_nosh
        )
        if is_new:
            months[month_key]["positive_new"] += 1

        confirmed_in_nosh.add(visit.place_id)

    return [
        ProgressResponse(
            month=month,
            confirmed_positive_new_count=data["positive_new"],
            total_confirmed_count=data["total"],
        )
        for month, data in sorted(months.items())
    ]


async def _upsert_place_state(
    db: AsyncSession, user_id: uuid.UUID, place_id: uuid.UUID, state: str, source: str
) -> None:
    result = await db.execute(
        select(UserPlaceState).where(
            UserPlaceState.user_id == user_id,
            UserPlaceState.place_id == place_id,
        )
    )
    row = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if row is None:
        was_before = source == "onboarding" and state == "visited"
        db.add(
            UserPlaceState(
                user_id=user_id,
                place_id=place_id,
                state=state,
                source=source,
                was_visited_before_nosh=was_before,
                occurred_at=now,
            )
        )
    else:
        row.state = state
        row.source = source
        row.occurred_at = now
        # Never reset was_visited_before_nosh once TRUE.
        if source == "onboarding" and state == "visited":
            row.was_visited_before_nosh = True


async def _to_response(db: AsyncSession, visit: Visit) -> VisitResponse:
    place_result = await db.execute(select(Place).where(Place.id == visit.place_id))
    place = place_result.scalar_one_or_none()
    return VisitResponse(
        id=visit.id,
        place_id=visit.place_id,
        place_name=place.canonical_name if place else str(visit.place_id),
        proposal_id=visit.proposal_id,
        visited_at=visit.visited_at,
        rating=visit.rating,
        confirmation_source=visit.confirmation_source,
        created_at=visit.created_at,
        corrected_at=visit.corrected_at,
    )
