from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import v1_router
from app.config import get_settings
from app.core.database import get_engine
from app.core.errors import NoshError, nosh_error_handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Validate auth configuration at startup; fail loudly rather than silently
    # accepting requests with broken auth.
    get_settings().validate_auth_config()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Nosh API",
        version=settings.api_version,
        description="Proactive restaurant-discovery backend",
        lifespan=lifespan,
    )

    # CORS: only add when origins are explicitly configured.  A native mobile
    # app does not make cross-origin requests.  Wildcard origins with
    # credentials are unsafe; we require explicit configuration.
    origins = settings.allowed_origins
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        )

    app.add_exception_handler(NoshError, nosh_error_handler)  # type: ignore[arg-type]

    @app.get("/health/live", tags=["health"])
    async def liveness() -> dict[str, Any]:
        return {"status": "ok", "version": settings.api_version}

    @app.get("/health/ready", tags=["health"])
    async def readiness() -> dict[str, Any]:
        try:
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "ok", "database": "connected"}
        except Exception as exc:
            # Return a generic message; do not leak raw DB error details.
            raise HTTPException(
                status_code=503,
                detail={"status": "unavailable"},
            ) from exc

    app.include_router(v1_router)

    return app


app = create_app()
