"""Test configuration and fixtures.

Unit tests run without a database.
Integration tests (marked @pytest.mark.integration) require DATABASE_URL.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient


def _dev_user_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def user_id() -> uuid.UUID:
    return _dev_user_id()


@pytest.fixture
def auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}"}


@pytest.fixture
def app():
    os.environ["AUTH_LOCAL_DEV"] = "true"
    os.environ["APP_ENVIRONMENT"] = "local"
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+asyncpg://nosh:nosh_dev@localhost:5432/nosh_test"
    )
    # Clear the lru_cache so the test env vars are picked up.
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import create_app

    return create_app()


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def async_client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# --- Integration DB fixture ---


@pytest_asyncio.fixture
async def db_session():
    """Async DB session connected to the test database. Rolls back after each test."""
    pytest.importorskip("asyncpg")
    db_url = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://nosh:nosh_dev@localhost:5432/nosh_test"
    )
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
