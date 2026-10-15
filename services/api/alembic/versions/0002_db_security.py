"""Revoke Supabase Data API access from all product tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-12

Strategy
--------
FastAPI connects as the ``postgres`` superuser (local Docker) or as a
Supabase service-role credential (production).  Both have full schema access.

The Supabase REST/Data API (PostgREST) runs as ``anon`` (unauthenticated
requests) or ``authenticated`` (requests carrying a Supabase JWT).  We block
both roles from every product table, sequence and routine.

Additionally, PostgreSQL grants EXECUTE on all new functions to PUBLIC by
default.  We revoke that default privilege so no schema function can be
called from the Data API without an explicit re-grant.

Changes applied
---------------
1. Revoke ALL on existing tables and sequences from anon and authenticated.
2. Revoke ALL on existing routines from anon, authenticated, and PUBLIC.
3. Set default privileges so future tables, sequences and routines created by
   any role are not auto-granted to anon, authenticated, or PUBLIC.

Guards
------
Each block is wrapped in ``IF EXISTS`` to remain a no-op on a plain local
PostgreSQL instance where those roles do not exist.

See DECISIONS.md D014.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REVOKE_SQL = """
DO $$
BEGIN
    -- ------------------------------------------------------------------ --
    -- Revoke existing privileges
    -- ------------------------------------------------------------------ --

    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM anon;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
        REVOKE ALL ON ALL ROUTINES  IN SCHEMA public FROM anon;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM authenticated;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM authenticated;
        REVOKE ALL ON ALL ROUTINES  IN SCHEMA public FROM authenticated;
    END IF;

    -- PostgreSQL grants EXECUTE on new routines to PUBLIC by default.
    -- Revoke this so PostgREST cannot call any schema function.
    REVOKE ALL ON ALL ROUTINES IN SCHEMA public FROM PUBLIC;

    -- ------------------------------------------------------------------ --
    -- Remove default privileges so future objects are not auto-granted
    -- ------------------------------------------------------------------ --

    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON TABLES    FROM anon;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON SEQUENCES FROM anon;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON ROUTINES  FROM anon;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON TABLES    FROM authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON SEQUENCES FROM authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE ALL ON ROUTINES  FROM authenticated;
    END IF;

    -- Revoke the PostgreSQL default EXECUTE-on-new-routine grant to PUBLIC.
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        REVOKE ALL ON ROUTINES FROM PUBLIC;
END
$$;
"""

# Downgrade restores Supabase-style default grants explicitly.
# This is intentional and must be reviewed before executing in production.
_RESTORE_SQL = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO anon;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT SELECT ON TABLES TO anon;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public
            TO authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
    END IF;

    -- Restore PostgreSQL default EXECUTE for PUBLIC.
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT EXECUTE ON ROUTINES TO PUBLIC;
END
$$;
"""


def upgrade() -> None:
    op.execute(_REVOKE_SQL)


def downgrade() -> None:
    op.execute(_RESTORE_SQL)
