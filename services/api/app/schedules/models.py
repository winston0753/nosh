from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import ARRAY, CheckConstraint, DateTime, Integer, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MealSchedule(Base):
    """One row per (user, meal type): when Nosh should help with that meal (D020, D026)."""

    __tablename__ = "meal_schedules"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    meal_type: Mapped[str] = mapped_column(String(20), primary_key=True)  # lunch/dinner
    enabled: Mapped[bool] = mapped_column(nullable=False)
    local_window_start: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    local_window_end: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    time_zone: Mapped[str] = mapped_column(String(100), nullable=False)  # IANA tz
    active_days: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)  # 0=Mon..6=Sun
    # Highest acceptable price level, 1 ($) to 4 ($$$$); NULL means no ceiling.
    price_ceiling: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    notifications_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("meal_type IN ('lunch', 'dinner')", name="ck_meal_schedules_meal_type"),
        CheckConstraint(
            "price_ceiling IS NULL OR price_ceiling BETWEEN 1 AND 4",
            name="ck_meal_schedules_price_ceiling",
        ),
    )


class SavedAnchor(Base):
    """Optional Home/Work spot, used only when the device location is unavailable (D020).

    The point is precise user data: never log it, and delete it with the account.
    """

    __tablename__ = "saved_anchors"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)  # home/work
    location: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (CheckConstraint("kind IN ('home', 'work')", name="ck_saved_anchors_kind"),)
