from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import Profile


async def get_or_create_profile(db: AsyncSession, user_id: uuid.UUID) -> Profile:
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def get_profile(db: AsyncSession, user_id: uuid.UUID) -> Profile | None:
    result = await db.execute(
        select(Profile).where(Profile.user_id == user_id, Profile.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def delete_account(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Hard-delete all user-owned data in dependency order.

    Deletion order matters:
      1. visits — references proposals (FK ON DELETE SET NULL since migration
         0003, so this is now safe regardless of order, but explicit first is
         clearer and avoids relying on the SET NULL timing).
      2. notification_deliveries — references suggestion_sessions (ON DELETE
         SET NULL), but references user_id directly; delete explicitly.
      3. dining_contexts — cascades:
           dining_contexts → suggestion_sessions → proposals → proposal_responses
         Precise coordinates in dining_contexts.location are erased here.
      4. user_place_states — no cascades.
      5. device_tokens — no cascades.
      6. profiles — must be last (FK target for Supabase Auth; or simply last
         to avoid orphan cleanup issues).

    NOTE: This endpoint removes product data.  For a full account deletion that
    also removes the Supabase Auth user record, call the Supabase Admin API with
    the service-role key.  This is not yet implemented; add it here when
    SUPABASE_SERVICE_ROLE_KEY is available.
    """
    from app.contexts.models import DiningContext
    from app.notifications.models import DeviceToken, NotificationDelivery
    from app.places.models import UserPlaceState
    from app.visits.models import Visit

    # 1. Visits first (references proposals, which will cascade-delete later).
    await db.execute(delete(Visit).where(Visit.user_id == user_id))

    # 2. Notification deliveries (not covered by any cascade).
    await db.execute(delete(NotificationDelivery).where(NotificationDelivery.user_id == user_id))

    # 3. Contexts (cascades → sessions → proposals → responses).
    await db.execute(delete(DiningContext).where(DiningContext.user_id == user_id))

    # 4. Place states.
    await db.execute(delete(UserPlaceState).where(UserPlaceState.user_id == user_id))

    # 5. Device tokens.
    await db.execute(delete(DeviceToken).where(DeviceToken.user_id == user_id))

    # 6. Profile last.
    await db.execute(delete(Profile).where(Profile.user_id == user_id))

    await db.commit()


async def soft_delete_profile(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Kept for backward compatibility; full deletion uses delete_account()."""
    await db.execute(
        update(Profile).where(Profile.user_id == user_id).values(deleted_at=datetime.now(UTC))
    )
    await db.commit()
