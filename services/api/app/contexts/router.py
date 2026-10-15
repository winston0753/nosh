from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.contexts import schemas, service
from app.core.database import get_db

router = APIRouter(prefix="/contexts", tags=["contexts"])


@router.get("", response_model=list[schemas.ContextResponse])
async def list_contexts(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> list[schemas.ContextResponse]:
    return await service.list_contexts(db, current_user)


@router.post("", response_model=schemas.ContextResponse, status_code=201)
async def create_context(
    body: schemas.ContextCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> schemas.ContextResponse:
    return await service.create_context(db, current_user, body)


@router.patch("/{context_id}", response_model=schemas.ContextResponse)
async def update_context(
    context_id: uuid.UUID,
    body: schemas.ContextUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> schemas.ContextResponse:
    return await service.update_context(db, context_id, current_user, body)


@router.delete("/{context_id}", status_code=204)
async def delete_context(
    context_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.delete_context(db, context_id, current_user)
