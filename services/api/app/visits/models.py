from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id"), nullable=False
    )
    # Migration 0003: FK changed to ON DELETE SET NULL so cascade-deleting
    # proposals (via account deletion) does not block visit deletion.
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("proposals.id", ondelete="SET NULL"), nullable=True
    )
    visited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmation_source: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # app_confirmation / manual
    rating: Mapped[str | None] = mapped_column(String(50), nullable=True)  # positive / negative
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_visits_user_id", "user_id"),
        Index("ix_visits_place_id", "place_id"),
        # Migration 0003: one confirmed visit per user per accepted proposal.
        # PostgreSQL partial unique index — only non-null proposal_id values are
        # constrained, so manual visits (proposal_id=NULL) are unrestricted.
        Index(
            "uq_visits_user_proposal",
            "user_id",
            "proposal_id",
            unique=True,
            postgresql_where=text("proposal_id IS NOT NULL"),
        ),
    )
