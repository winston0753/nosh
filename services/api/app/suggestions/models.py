from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SuggestionSession(Base):
    __tablename__ = "suggestion_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    meal_window_key: Mapped[str] = mapped_column(String(50), nullable=False)  # YYYY-MM-DD#meal_type
    # Version of the user's meal_schedules row for this meal when the session began.
    schedule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Where the session was anchored: device (foreground location), home, or
    # work; legacy_context for sessions migrated from dining contexts.
    # The coordinate itself is never stored on the session (D017).
    anchor_source: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    # Ranked candidates not yet proposed, computed once at creation (D022).
    # Another and Been here already take the next entry, so the anchor point
    # is never needed again.  Emptied when the session closes.
    candidate_queue: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    proposals: Mapped[list[Proposal]] = relationship("Proposal", back_populates="session")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "meal_window_key", name="uq_suggestion_sessions_user_meal_window"
        ),
    )


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suggestion_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suggestion_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id"), nullable=False
    )
    cuisine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cuisines.id"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[float] = mapped_column(nullable=False)
    score_components: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    candidate_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[SuggestionSession] = relationship(
        "SuggestionSession", back_populates="proposals"
    )
    response: Mapped[ProposalResponse | None] = relationship(
        "ProposalResponse", back_populates="proposal", uselist=False
    )

    __table_args__ = (UniqueConstraint("suggestion_session_id", "sequence_number"),)


class ProposalResponse(Base):
    __tablename__ = "proposal_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # go/another/not_today/been_here
    response: Mapped[str] = mapped_column(String(50), nullable=False)
    client_event_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    responded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    proposal: Mapped[Proposal] = relationship("Proposal", back_populates="response")

    # Migration 0003: one response per proposal.
    __table_args__ = (UniqueConstraint("proposal_id", name="uq_proposal_responses_proposal_id"),)
