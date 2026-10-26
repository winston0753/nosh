from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.users import schemas, service

router = APIRouter(prefix="/me", tags=["users"])


@router.get("", response_model=schemas.ProfileResponse)
async def get_me(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> schemas.ProfileResponse:
    profile = await service.get_or_create_profile(db, current_user)
    return schemas.ProfileResponse.model_validate(profile)


@router.delete("/product-data", status_code=204)
async def delete_my_product_data(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> None:
    """Delete all Nosh product data owned by the current user.

    This endpoint removes: suggestion sessions (cascades to proposals and
    responses), the meal schedule, saved Home/Work spots, visits, notification
    deliveries, place states, device tokens, and the Nosh profile row.

    It does NOT delete the Supabase Auth identity.  A user with a valid token
    can still authenticate after calling this endpoint; they will receive a
    fresh profile on next access.  Full identity deletion requires calling the
    Supabase Admin API with a service-role credential, which is not yet
    implemented (see notes.md for the planned capability).
    """
    await service.delete_account(db, current_user)
