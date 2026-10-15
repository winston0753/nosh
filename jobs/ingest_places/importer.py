"""Place ingestor — loads fixture data into the database on startup."""

from __future__ import annotations

import asyncio
import os
import sys

# Allow running as a script: python -m jobs.ingest_places.importer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


async def main() -> None:
    """Load fixture data into the database."""
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+asyncpg://nosh:nosh_dev@localhost:5432/nosh_dev"
    )
    os.environ["AUTH_LOCAL_DEV"] = "true"

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from services.api.app.config import get_settings
    from services.api.app.places.service import load_fixture_data

    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, echo=True)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        await load_fixture_data(db)
        print("Fixture data loaded.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
