"""Place ingestor — idempotently loads the curated fixture catalog.

Supported invocation (from ``services/api``, the API's uv project root)::

    DATABASE_URL=postgresql+asyncpg://nosh:nosh_dev@localhost:5432/nosh_dev \\
      uv run --frozen python -m jobs.ingest_places.importer

``jobs`` lives inside the API project and imports the application as the
top-level ``app`` package, exactly as the API and its tests do.  It must never
import through ``services.api.app``: that would load a second, incompatible
copy of every module.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.places.service import load_fixture_data


async def main() -> None:
    """Load fixture places and cuisines into the configured database."""
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as db:
            await load_fixture_data(db)
    finally:
        await engine.dispose()
    print("Fixture data loaded.")


if __name__ == "__main__":
    asyncio.run(main())
