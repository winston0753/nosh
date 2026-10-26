from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import all models so metadata is populated
from app.core.database import Base
from app.notifications.models import DeviceToken, NotificationDelivery  # noqa: F401
from app.places.models import Cuisine, Place, PlaceCuisine, PlaceSource, UserPlaceState  # noqa: F401
from app.schedules.models import MealSchedule, SavedAnchor  # noqa: F401
from app.suggestions.models import Proposal, ProposalResponse, SuggestionSession  # noqa: F401
from app.users.models import Profile  # noqa: F401
from app.visits.models import Visit  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override URL from DATABASE_URL env var if set (for CI and local dev).
db_url = os.getenv("DATABASE_URL")
if db_url:
    import re

    db_url = re.sub(r"^postgresql(\+\w+)?://", "postgresql+psycopg2://", db_url)
    config.set_main_option("sqlalchemy.url", db_url)


# ---------------------------------------------------------------------------
# Extension-object filter
# ---------------------------------------------------------------------------

# The postgis/postgis Docker image installs PostGIS, Tiger Geocoder, and
# PostGIS Topology extensions which create tables across three schemas:
#   public   — spatial_ref_sys (PostGIS core)
#   tiger    — US geocoder lookup tables (dozens of tables)
#   topology — topology layer/relation tables
#
# Alembic autogenerate must see only Nosh application tables; extension-owned
# objects must never appear as "detected removed" and must never be dropped.
#
# Strategy: ignore every object whose enclosing table is not in our ORM
# metadata.  The metadata only contains Nosh-owned tables in the public
# schema, so extension schemas (tiger, topology) and the PostGIS
# spatial_ref_sys table are naturally excluded.

_APP_TABLE_NAMES: frozenset[str] = frozenset(target_metadata.tables.keys())

# Schemas that contain only extension-owned objects — always excluded.
_EXTENSION_SCHEMAS = frozenset({"tiger", "tiger_data", "topology"})


def include_object(
    object: object,
    name: str,
    type_: str,
    reflected: bool,
    compare_to: object,
) -> bool:
    """Return True only for Nosh application objects.

    Rules:
    - Tables in tiger / tiger_data / topology schemas → excluded.
    - Tables in public not in our ORM metadata (e.g. spatial_ref_sys) → excluded.
    - All columns, indexes, constraints, FK, sequences belonging to an excluded
      table are excluded transitively (Alembic skips child objects automatically
      when the parent table is excluded).
    """
    if type_ == "table":
        schema = getattr(object, "schema", None)
        if schema in _EXTENSION_SCHEMAS:
            return False
        # For public-schema tables, only include Nosh application tables.
        # spatial_ref_sys and any other extension-created public tables are
        # excluded by not being in our ORM metadata.
        return name in _APP_TABLE_NAMES
    return True


# ---------------------------------------------------------------------------
# Standard Alembic offline / online runners
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
