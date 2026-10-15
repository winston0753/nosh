"""Idempotency constraints and FK fixes.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-12

Changes:
1. proposal_responses: add UNIQUE(proposal_id) so at most one response can
   exist per proposal.  The existing UNIQUE(client_event_id) remains.

2. visits: change the FK on proposal_id from implicit RESTRICT to SET NULL so
   that cascading proposal deletes (triggered by account deletion) do not
   violate this constraint.

3. visits: add a partial unique index on (user_id, proposal_id) WHERE
   proposal_id IS NOT NULL to prevent concurrent duplicate visit confirmations
   for the same accepted proposal.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. One response per proposal at the database level.
    op.create_unique_constraint(
        "uq_proposal_responses_proposal_id", "proposal_responses", ["proposal_id"]
    )

    # 2. Fix visits.proposal_id FK: RESTRICT → SET NULL.
    #    Drop the implicit FK (Alembic names it automatically) and recreate.
    op.drop_constraint("visits_proposal_id_fkey", "visits", type_="foreignkey")
    op.create_foreign_key(
        "visits_proposal_id_fkey",
        "visits",
        "proposals",
        ["proposal_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3. Partial unique index: one visit per user per accepted proposal.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_visits_user_proposal
            ON visits (user_id, proposal_id)
            WHERE proposal_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_visits_user_proposal")

    op.drop_constraint("visits_proposal_id_fkey", "visits", type_="foreignkey")
    op.create_foreign_key(
        "visits_proposal_id_fkey",
        "visits",
        "proposals",
        ["proposal_id"],
        ["id"],
    )

    op.drop_constraint(
        "uq_proposal_responses_proposal_id", "proposal_responses", type_="unique"
    )
