"""Add was_visited_before_nosh to user_place_states.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-12

Background
----------
The North Star metric counts confirmed positively rated *new* restaurant
visits — new meaning the user had not been there before using Nosh.

A UserPlaceState row can have source='onboarding' when the user marked a
place as 'Been' during the onboarding flow.  The existing code overwrites
source to 'confirmation' when a later Nosh visit is confirmed, erasing the
provenance record and causing the metric to incorrectly count the visit as new.

Fix
---
Add ``was_visited_before_nosh BOOLEAN NOT NULL DEFAULT FALSE``.

Rules:
- Set TRUE when source='onboarding' creates or updates the row to state='visited'.
- Never reset to FALSE when a later confirmation updates the row.
- The progress metric reads this flag directly instead of inferring from source.

Backfill
--------
Existing rows where source='onboarding' AND state='visited' are backfilled to
was_visited_before_nosh=TRUE.

See notes.md for full rationale.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_place_states",
        sa.Column(
            "was_visited_before_nosh",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
    )
    # Backfill: rows that already record an onboarding-sourced visit were there
    # before the user started using Nosh.
    op.execute(
        """
        UPDATE user_place_states
        SET was_visited_before_nosh = TRUE
        WHERE source = 'onboarding' AND state = 'visited'
        """
    )


def downgrade() -> None:
    op.drop_column("user_place_states", "was_visited_before_nosh")
