from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.visits import schemas, service

router = APIRouter(tags=["visits"])


@router.post("/visits", response_model=schemas.VisitResponse, status_code=201)
async def create_visit(
    body: schemas.VisitCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> schemas.VisitResponse:
    return await service.confirm_visit(db, current_user, body)


@router.patch("/visits/{visit_id}", response_model=schemas.VisitResponse)
async def update_visit(
    visit_id: uuid.UUID,
    body: schemas.VisitUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> schemas.VisitResponse:
    return await service.update_visit(db, current_user, visit_id, body)


@router.get("/visits", response_model=list[schemas.VisitResponse])
async def list_visits(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, le=100),
    cursor: uuid.UUID | None = None,
) -> list[schemas.VisitResponse]:
    return await service.list_visits(db, current_user, limit=limit, cursor=cursor)


@router.get("/progress", response_model=list[schemas.ProgressResponse])
async def get_progress(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[schemas.ProgressResponse]:
    return await service.get_progress(db, current_user)
