"""Replace dining contexts with a per-user meal schedule (D020, D022, D026).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-25

Changes
-------
- New ``meal_schedules``: one row per (user, lunch|dinner) with window, IANA
  time zone, active days, price ceiling (1–4 or NULL), and notification flag.
- New ``saved_anchors``: optional Home/Work points, used only when the device
  location is unavailable.
- ``suggestion_sessions`` is keyed by ``(user_id, meal_window_key)`` instead
  of ``(dining_context_id, meal_window_key)``.  It gains ``schedule_version``
  (replacing ``context_version``), ``anchor_source``, and ``candidate_queue``
  (the ranked candidates not yet proposed; D022).
- ``dining_contexts`` is dropped.

Data
----
Each user's most recently created enabled lunch and dinner context becomes
that meal's schedule row (brunch contexts are dropped; Home/Work are not
inferred from context points).  Where one user had sessions for the same
meal window under several contexts, only the earliest is kept; the others
are deleted with their proposals and responses (visits keep their rows, with
``proposal_id`` set to NULL by the existing foreign key).  Existing sessions
get ``anchor_source = 'legacy_context'`` and an empty candidate queue, so a
still-active legacy session ends as ``exhausted`` on its next Another.

Downgrade
---------
Recreates ``dining_contexts`` with one context per (user, meal type) that has
a schedule row or a session, anchored at the user's saved Home (else Work,
else 0,0) point, and re-links sessions to them.  ``saved_anchors``,
``meal_schedules``, the price ceiling, and candidate queues are lost.
"""

from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_SESSION_UNIQUE = "suggestion_sessions_dining_context_id_meal_window_key_key"
_NEW_SESSION_UNIQUE = "uq_suggestion_sessions_user_meal_window"


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "meal_schedules",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meal_type", sa.String(20), primary_key=True),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("local_window_start", sa.String(5), nullable=False),
        sa.Column("local_window_end", sa.String(5), nullable=False),
        sa.Column("time_zone", sa.String(100), nullable=False),
        sa.Column("active_days", postgresql.ARRAY(sa.Integer), nullable=False),
        sa.Column("price_ceiling", sa.SmallInteger, nullable=True),
        sa.Column("notifications_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        *_timestamps(),
        sa.CheckConstraint("meal_type IN ('lunch', 'dinner')", name="ck_meal_schedules_meal_type"),
        sa.CheckConstraint(
            "price_ceiling IS NULL OR price_ceiling BETWEEN 1 AND 4",
            name="ck_meal_schedules_price_ceiling",
        ),
    )
    op.create_table(
        "saved_anchors",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(20), primary_key=True),
        sa.Column(
            "location", geoalchemy2.Geography(geometry_type="POINT", srid=4326), nullable=False
        ),
        *_timestamps(),
        sa.CheckConstraint("kind IN ('home', 'work')", name="ck_saved_anchors_kind"),
    )

    op.execute(
        """
        INSERT INTO meal_schedules (
            user_id, meal_type, enabled, local_window_start, local_window_end,
            time_zone, active_days, notifications_enabled
        )
        SELECT DISTINCT ON (user_id, meal_type)
            user_id, meal_type, TRUE, local_window_start, local_window_end,
            time_zone, active_days, notifications_enabled
        FROM dining_contexts
        WHERE disabled_at IS NULL AND meal_type IN ('lunch', 'dinner')
        ORDER BY user_id, meal_type, created_at DESC, id
        """
    )

    # Keep one session per (user, meal window): the earliest.
    op.execute(
        """
        DELETE FROM suggestion_sessions s
        USING suggestion_sessions keep
        WHERE keep.user_id = s.user_id
          AND keep.meal_window_key = s.meal_window_key
          AND (keep.created_at, keep.id) < (s.created_at, s.id)
        """
    )

    op.add_column("suggestion_sessions", sa.Column("schedule_version", sa.Integer, nullable=True))
    op.add_column("suggestion_sessions", sa.Column("anchor_source", sa.String(20), nullable=True))
    op.add_column(
        "suggestion_sessions",
        sa.Column(
            "candidate_queue",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.execute(
        "UPDATE suggestion_sessions "
        "SET schedule_version = context_version, anchor_source = 'legacy_context'"
    )
    op.alter_column("suggestion_sessions", "schedule_version", nullable=False)
    op.alter_column("suggestion_sessions", "anchor_source", nullable=False)

    # Dropping the column also drops the old (dining_context_id, meal_window_key)
    # unique constraint and the foreign key.
    op.drop_column("suggestion_sessions", "dining_context_id")
    op.drop_column("suggestion_sessions", "context_version")
    op.create_unique_constraint(
        _NEW_SESSION_UNIQUE, "suggestion_sessions", ["user_id", "meal_window_key"]
    )

    op.drop_index("ix_dining_contexts_location", table_name="dining_contexts")
    op.drop_index("ix_dining_contexts_user_id", table_name="dining_contexts")
    op.drop_table("dining_contexts")


def downgrade() -> None:
    op.create_table(
        "dining_contexts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("meal_type", sa.String(50), nullable=False),
        sa.Column(
            "location", geoalchemy2.Geography(geometry_type="POINT", srid=4326), nullable=False
        ),
        sa.Column("radius_meters", sa.Integer, nullable=False, server_default="1600"),
        sa.Column("local_window_start", sa.String(5), nullable=False),
        sa.Column("local_window_end", sa.String(5), nullable=False),
        sa.Column("time_zone", sa.String(100), nullable=False),
        sa.Column("active_days", postgresql.ARRAY(sa.Integer), nullable=False),
        sa.Column("notifications_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_dining_contexts_user_id", "dining_contexts", ["user_id"])
    op.create_index(
        "ix_dining_contexts_location", "dining_contexts", ["location"], postgresql_using="gist"
    )

    op.execute(
        """
        INSERT INTO dining_contexts (
            user_id, name, meal_type, location, local_window_start, local_window_end,
            time_zone, active_days, notifications_enabled, version, disabled_at
        )
        SELECT
            u.user_id,
            initcap(u.meal_type),
            u.meal_type,
            COALESCE(
                (SELECT a.location FROM saved_anchors a
                 WHERE a.user_id = u.user_id ORDER BY a.kind = 'home' DESC LIMIT 1),
                'SRID=4326;POINT(0 0)'::geography
            ),
            COALESCE(m.local_window_start,
                     CASE u.meal_type WHEN 'dinner' THEN '17:30' ELSE '11:30' END),
            COALESCE(m.local_window_end,
                     CASE u.meal_type WHEN 'dinner' THEN '20:30' ELSE '13:30' END),
            COALESCE(m.time_zone, 'UTC'),
            COALESCE(m.active_days, ARRAY[0, 1, 2, 3, 4, 5, 6]),
            COALESCE(m.notifications_enabled, TRUE),
            COALESCE(m.version, 1),
            CASE WHEN COALESCE(m.enabled, FALSE) THEN NULL ELSE now() END
        FROM (
            SELECT user_id, meal_type FROM meal_schedules
            UNION
            SELECT user_id, split_part(meal_window_key, '#', 2) FROM suggestion_sessions
        ) u
        LEFT JOIN meal_schedules m ON m.user_id = u.user_id AND m.meal_type = u.meal_type
        """
    )

    op.drop_constraint(_NEW_SESSION_UNIQUE, "suggestion_sessions", type_="unique")
    op.add_column(
        "suggestion_sessions",
        sa.Column("dining_context_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("suggestion_sessions", sa.Column("context_version", sa.Integer, nullable=True))
    op.execute(
        """
        UPDATE suggestion_sessions s
        SET dining_context_id = c.id, context_version = s.schedule_version
        FROM dining_contexts c
        WHERE c.user_id = s.user_id
          AND c.meal_type = split_part(s.meal_window_key, '#', 2)
        """
    )
    op.alter_column("suggestion_sessions", "dining_context_id", nullable=False)
    op.alter_column("suggestion_sessions", "context_version", nullable=False)
    op.create_foreign_key(
        "suggestion_sessions_dining_context_id_fkey",
        "suggestion_sessions",
        "dining_contexts",
        ["dining_context_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        _OLD_SESSION_UNIQUE, "suggestion_sessions", ["dining_context_id", "meal_window_key"]
    )
    op.drop_column("suggestion_sessions", "candidate_queue")
    op.drop_column("suggestion_sessions", "anchor_source")
    op.drop_column("suggestion_sessions", "schedule_version")

    op.drop_table("saved_anchors")
    op.drop_table("meal_schedules")
