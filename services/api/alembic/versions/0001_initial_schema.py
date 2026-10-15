"""Initial schema: all phase-one tables.

Revision ID: 0001
Revises:
Create Date: 2026-10-12
"""

from __future__ import annotations

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostGIS is pre-installed in the postgis/postgis Docker image.
    # pgvector is deferred; see DECISIONS.md D013.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # profiles
    op.create_table(
        "profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("onboarding_state", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # places
    op.create_table(
        "places",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geography(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_places_location", "places", ["location"], postgresql_using="gist")

    # place_sources
    op.create_table(
        "place_sources",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "place_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("places.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("provider_place_id", sa.String(255), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("provider", "provider_place_id"),
    )

    # cuisines
    op.create_table(
        "cuisines",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cuisines.id"),
            nullable=True,
        ),
    )

    # place_cuisines
    op.create_table(
        "place_cuisines",
        sa.Column(
            "place_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("places.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "cuisine_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cuisines.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="true"),
    )

    # dining_contexts
    op.create_table(
        "dining_contexts",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("meal_type", sa.String(50), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geography(geometry_type="POINT", srid=4326),
            nullable=False,
        ),
        sa.Column("radius_meters", sa.Integer, nullable=False, server_default="1600"),
        sa.Column("local_window_start", sa.String(5), nullable=False),
        sa.Column("local_window_end", sa.String(5), nullable=False),
        sa.Column("time_zone", sa.String(100), nullable=False),
        sa.Column("active_days", postgresql.ARRAY(sa.Integer), nullable=False),
        sa.Column(
            "notifications_enabled", sa.Boolean, nullable=False, server_default="true"
        ),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_dining_contexts_user_id", "dining_contexts", ["user_id"])
    op.create_index(
        "ix_dining_contexts_location",
        "dining_contexts",
        ["location"],
        postgresql_using="gist",
    )

    # user_place_states
    op.create_table(
        "user_place_states",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "place_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("places.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("state", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # suggestion_sessions
    op.create_table(
        "suggestion_sessions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "dining_context_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dining_contexts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("context_version", sa.Integer, nullable=False),
        sa.Column("meal_window_key", sa.String(50), nullable=False),
        sa.Column("state", sa.String(50), nullable=False, server_default="active"),
        sa.Column("policy_version", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("dining_context_id", "meal_window_key"),
    )

    # proposals
    op.create_table(
        "proposals",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "suggestion_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suggestion_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "place_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("places.id"),
            nullable=False,
        ),
        sa.Column(
            "cuisine_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cuisines.id"),
            nullable=False,
        ),
        sa.Column("sequence_number", sa.Integer, nullable=False),
        sa.Column("total_score", sa.Float, nullable=False),
        sa.Column("score_components", postgresql.JSONB, nullable=False),
        sa.Column(
            "reason_codes",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("candidate_snapshot", postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("suggestion_session_id", "sequence_number"),
    )

    # proposal_responses
    op.create_table(
        "proposal_responses",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response", sa.String(50), nullable=False),
        sa.Column("client_event_id", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "responded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # visits
    op.create_table(
        "visits",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "place_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("places.id"),
            nullable=False,
        ),
        sa.Column(
            "proposal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("proposals.id"),
            nullable=True,
        ),
        sa.Column("visited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmation_source", sa.String(50), nullable=False),
        sa.Column("rating", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_visits_user_id", "visits", ["user_id"])
    op.create_index("ix_visits_place_id", "visits", ["place_id"])

    # device_tokens
    op.create_table(
        "device_tokens",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("expo_push_token", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
    )

    # notification_deliveries
    op.create_table(
        "notification_deliveries",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "suggestion_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suggestion_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("deduplication_key", sa.String(255), nullable=False, unique=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("state", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("notification_deliveries")
    op.drop_table("device_tokens")
    op.drop_index("ix_visits_place_id", table_name="visits")
    op.drop_index("ix_visits_user_id", table_name="visits")
    op.drop_table("visits")
    op.drop_table("proposal_responses")
    op.drop_table("proposals")
    op.drop_table("suggestion_sessions")
    op.drop_table("user_place_states")
    op.drop_index("ix_dining_contexts_location", table_name="dining_contexts")
    op.drop_index("ix_dining_contexts_user_id", table_name="dining_contexts")
    op.drop_table("dining_contexts")
    op.drop_table("place_cuisines")
    op.drop_table("cuisines")
    op.drop_table("place_sources")
    op.drop_index("ix_places_location", table_name="places")
    op.drop_table("places")
    op.drop_table("profiles")
