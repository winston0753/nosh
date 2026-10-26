from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.schedules import schemas, service

router = APIRouter(prefix="/me", tags=["schedule"])


@router.get("/meal-schedule", response_model=schemas.MealScheduleResponse)
async def get_meal_schedule(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> schemas.MealScheduleResponse:
    return await service.get_meal_schedule(db, current_user)


@router.put("/meal-schedule", response_model=schemas.MealScheduleResponse)
async def replace_meal_schedule(
    body: schemas.MealScheduleUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> schemas.MealScheduleResponse:
    return await service.replace_meal_schedule(db, current_user, body)


@router.get("/anchors", response_model=list[schemas.AnchorResponse])
async def list_anchors(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> list[schemas.AnchorResponse]:
    return await service.list_anchors(db, current_user)


@router.put("/anchors/{kind}", response_model=schemas.AnchorResponse)
async def set_anchor(
    kind: schemas.AnchorKind,
    body: schemas.AnchorIn,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> schemas.AnchorResponse:
    return await service.set_anchor(db, current_user, kind, body)


@router.delete("/anchors/{kind}", status_code=204)
async def delete_anchor(
    kind: schemas.AnchorKind,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.delete_anchor(db, current_user, kind)
