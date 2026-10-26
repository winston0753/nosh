from __future__ import annotations

import uuid

from sqlalchemy import Float, delete, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import Label

from app.core.errors import ValidationFailedError
from app.schedules.models import MealSchedule, SavedAnchor
from app.schedules.schemas import (
    AnchorIn,
    AnchorResponse,
    MealPlan,
    MealScheduleResponse,
    MealScheduleUpdate,
)
from app.schedules.validation import windows_overlap

# Columns a schedule update may change; a change to any of them bumps version.
_PLAN_FIELDS = (
    "enabled",
    "local_window_start",
    "local_window_end",
    "time_zone",
    "active_days",
    "price_ceiling",
    "notifications_enabled",
)


async def get_meal_schedule(db: AsyncSession, user_id: uuid.UUID) -> MealScheduleResponse:
    result = await db.execute(
        select(MealSchedule)
        .where(MealSchedule.user_id == user_id)
        .order_by(MealSchedule.meal_type.desc())  # lunch before dinner
        .execution_options(populate_existing=True)
    )
    return MealScheduleResponse(
        meals=[MealPlan.model_validate(row) for row in result.scalars().all()]
    )


async def replace_meal_schedule(
    db: AsyncSession, user_id: uuid.UUID, body: MealScheduleUpdate
) -> MealScheduleResponse:
    """Replace the user's schedule.  Idempotent: an identical PUT changes nothing.

    Each meal is upserted atomically; its version increases only when a stored
    value actually changes.  Meal types absent from the body are deleted.
    """
    enabled = [m for m in body.meals if m.enabled]
    for i, a in enumerate(enabled):
        for b in enabled[i + 1 :]:
            shared_days = set(a.active_days) & set(b.active_days)
            if shared_days and windows_overlap(
                a.local_window_start, a.local_window_end, b.local_window_start, b.local_window_end
            ):
                raise ValidationFailedError(
                    f"{a.meal_type} and {b.meal_type} windows overlap on a shared day",
                    field="meals",
                )

    table = MealSchedule.__table__
    for meal in body.meals:
        values = {
            "enabled": meal.enabled,
            "local_window_start": meal.local_window_start,
            "local_window_end": meal.local_window_end,
            "time_zone": body.time_zone,
            "active_days": meal.active_days,
            "price_ceiling": meal.price_ceiling,
            "notifications_enabled": meal.notifications_enabled,
        }
        stmt = pg_insert(MealSchedule).values(user_id=user_id, meal_type=meal.meal_type, **values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[table.c.user_id, table.c.meal_type],
            set_={
                **{field: stmt.excluded[field] for field in _PLAN_FIELDS},
                "version": table.c.version + 1,
                "updated_at": func.now(),
            },
            where=tuple_(*(table.c[f] for f in _PLAN_FIELDS)).is_distinct_from(
                tuple_(*(stmt.excluded[f] for f in _PLAN_FIELDS))
            ),
        )
        await db.execute(stmt)

    kept = [m.meal_type for m in body.meals]
    await db.execute(
        delete(MealSchedule).where(
            MealSchedule.user_id == user_id, MealSchedule.meal_type.not_in(kept)
        )
    )
    await db.commit()
    return await get_meal_schedule(db, user_id)


async def lock_meal_plan(
    db: AsyncSession, user_id: uuid.UUID, meal_type: str
) -> MealSchedule | None:
    """Return the user's plan for ``meal_type`` with a row lock, or None.

    Session creation holds this lock so concurrent requests for the same meal
    window serialise and exactly one session is inserted.
    """
    result = await db.execute(
        select(MealSchedule)
        .where(MealSchedule.user_id == user_id, MealSchedule.meal_type == meal_type)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


# --------------------------------------------------------------------------- #
# Home/Work anchors
# --------------------------------------------------------------------------- #


def _anchor_columns() -> tuple[Label[float], Label[float]]:
    geom = func.ST_GeomFromWKB(func.ST_AsBinary(SavedAnchor.location))
    return func.ST_X(geom, type_=Float).label("lon"), func.ST_Y(geom, type_=Float).label("lat")


async def list_anchors(db: AsyncSession, user_id: uuid.UUID) -> list[AnchorResponse]:
    lon, lat = _anchor_columns()
    result = await db.execute(
        select(SavedAnchor.kind, SavedAnchor.updated_at, lon, lat)
        .where(SavedAnchor.user_id == user_id)
        .order_by(SavedAnchor.kind)
    )
    return [
        AnchorResponse(
            kind=row.kind,
            latitude=float(row.lat),
            longitude=float(row.lon),
            updated_at=row.updated_at,
        )
        for row in result.all()
    ]


async def get_anchor_point(
    db: AsyncSession, user_id: uuid.UUID, kind: str
) -> tuple[float, float] | None:
    """Return the saved anchor as (longitude, latitude), or None if unset."""
    lon, lat = _anchor_columns()
    result = await db.execute(
        select(lon, lat).where(SavedAnchor.user_id == user_id, SavedAnchor.kind == kind)
    )
    row = result.one_or_none()
    return None if row is None else (float(row.lon), float(row.lat))


async def set_anchor(
    db: AsyncSession, user_id: uuid.UUID, kind: str, body: AnchorIn
) -> AnchorResponse:
    point = f"SRID=4326;POINT({body.longitude} {body.latitude})"
    stmt = pg_insert(SavedAnchor).values(user_id=user_id, kind=kind, location=point)
    stmt = stmt.on_conflict_do_update(
        index_elements=[SavedAnchor.__table__.c.user_id, SavedAnchor.__table__.c.kind],
        set_={"location": stmt.excluded.location, "updated_at": func.now()},
    )
    await db.execute(stmt)
    await db.commit()
    anchors = await list_anchors(db, user_id)
    return next(a for a in anchors if a.kind == kind)


async def delete_anchor(db: AsyncSession, user_id: uuid.UUID, kind: str) -> None:
    """Idempotent: deleting an unset anchor succeeds."""
    await db.execute(
        delete(SavedAnchor).where(SavedAnchor.user_id == user_id, SavedAnchor.kind == kind)
    )
    await db.commit()
