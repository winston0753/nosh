from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.suggestions import schemas, service

router = APIRouter(tags=["suggestions"])


@router.post(
    "/suggestion-sessions",
    response_model=schemas.SessionResponse,
    status_code=201,
)
async def create_or_get_session(
    body: schemas.SessionCreateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> schemas.SessionResponse:
    session = await service.get_or_create_session(
        db, current_user, body.dining_context_id, body.meal_window_key
    )
    result = await service.session_to_response(db, session)
    return result  # type: ignore[return-value]


@router.get(
    "/suggestion-sessions/{session_id}",
    response_model=schemas.SessionResponse,
)
async def get_session(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> schemas.SessionResponse:
    session = await service.get_session(db, session_id, current_user)
    result = await service.session_to_response(db, session)
    return result  # type: ignore[return-value]


@router.post(
    "/proposals/{proposal_id}/responses",
    response_model=schemas.ResponseResult,
    status_code=201,
)
async def respond_to_proposal(
    proposal_id: uuid.UUID,
    body: schemas.ResponseRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> schemas.ResponseResult:
    session, resp, next_proposal = await service.record_response(
        db, proposal_id, current_user, body.response, body.client_event_id
    )
    return schemas.ResponseResult(
        response=resp.response,
        session_state=session.state,
        next_proposal=next_proposal,
        no_candidates=session.state == "exhausted",
    )
