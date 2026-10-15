from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import ARRAY, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DiningContext(Base):
    __tablename__ = "dining_contexts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(50), nullable=False)  # lunch/dinner/brunch
    location: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=False
    )
    radius_meters: Mapped[int] = mapped_column(Integer, default=1600, nullable=False)
    local_window_start: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    local_window_end: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    time_zone: Mapped[str] = mapped_column(String(100), nullable=False)  # IANA tz
    active_days: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)  # 0=Mon..6=Sun
    notifications_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_dining_contexts_user_id", "user_id"),
        Index("ix_dining_contexts_location", "location", postgresql_using="gist"),
    )
