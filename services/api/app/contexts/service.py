from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.models import DiningContext
from app.contexts.schemas import ContextCreate, ContextResponse, ContextUpdate
from app.core.errors import ForbiddenError, NotFoundError


async def create_context(
    db: AsyncSession, user_id: uuid.UUID, body: ContextCreate
) -> ContextResponse:
    ctx = DiningContext(
        user_id=user_id,
        name=body.name,
        meal_type=body.meal_type,
        location=f"SRID=4326;POINT({body.longitude} {body.latitude})",
        radius_meters=body.radius_meters,
        local_window_start=body.local_window_start,
        local_window_end=body.local_window_end,
        time_zone=body.time_zone,
        active_days=body.active_days,
        notifications_enabled=body.notifications_enabled,
    )
    db.add(ctx)
    await db.commit()
    await db.refresh(ctx)
    return await _to_response(db, ctx)


async def list_contexts(db: AsyncSession, user_id: uuid.UUID) -> list[ContextResponse]:
    result = await db.execute(select(DiningContext).where(DiningContext.user_id == user_id))
    return [await _to_response(db, ctx) for ctx in result.scalars().all()]


async def get_context_for_user(
    db: AsyncSession, context_id: uuid.UUID, user_id: uuid.UUID
) -> DiningContext:
    result = await db.execute(select(DiningContext).where(DiningContext.id == context_id))
    ctx = result.scalar_one_or_none()
    if ctx is None:
        raise NotFoundError("context", str(context_id))
    if ctx.user_id != user_id:
        raise ForbiddenError()
    return ctx


async def update_context(
    db: AsyncSession,
    context_id: uuid.UUID,
    user_id: uuid.UUID,
    body: ContextUpdate,
) -> ContextResponse:
    ctx = await get_context_for_user(db, context_id, user_id)
    changed = False
    for field, value in body.model_dump(exclude_none=True).items():
        if hasattr(ctx, field):
            setattr(ctx, field, value)
            changed = True
    if changed:
        ctx.version += 1
    await db.commit()
    await db.refresh(ctx)
    return await _to_response(db, ctx)


async def delete_context(db: AsyncSession, context_id: uuid.UUID, user_id: uuid.UUID) -> None:
    from datetime import UTC, datetime

    ctx = await get_context_for_user(db, context_id, user_id)
    ctx.disabled_at = datetime.now(UTC)
    await db.commit()


async def _to_response(db: AsyncSession, ctx: DiningContext) -> ContextResponse:
    """Extract lat/lon from PostGIS geography and build the response schema."""
    result = await db.execute(
        select(
            func.ST_X(func.ST_GeomFromWKB(func.ST_AsBinary(DiningContext.location))).label("lon"),
            func.ST_Y(func.ST_GeomFromWKB(func.ST_AsBinary(DiningContext.location))).label("lat"),
        ).where(DiningContext.id == ctx.id)
    )
    row = result.one()
    return ContextResponse(
        id=ctx.id,
        name=ctx.name,
        meal_type=ctx.meal_type,
        longitude=float(row.lon),
        latitude=float(row.lat),
        radius_meters=ctx.radius_meters,
        local_window_start=ctx.local_window_start,
        local_window_end=ctx.local_window_end,
        time_zone=ctx.time_zone,
        active_days=ctx.active_days,
        notifications_enabled=ctx.notifications_enabled,
        version=ctx.version,
        disabled_at=ctx.disabled_at,
        created_at=ctx.created_at,
    )
