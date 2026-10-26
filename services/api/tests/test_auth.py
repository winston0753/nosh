"""Unit tests for JWT authentication — no database required."""

from __future__ import annotations

import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest

_SECRET = "test-secret-must-be-long-enough-for-hs256-validation"
_ISSUER = "https://example.supabase.co/auth/v1"
_SUPABASE_URL = "https://example.supabase.co"
_USER_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")


def _make_token(
    *,
    sub: str | None = str(_USER_ID),
    iss: str | None = _ISSUER,
    aud: str | list[str] = "authenticated",
    role: str | None = "authenticated",
    exp_offset: int = 3600,
    secret: str = _SECRET,
    algorithm: str = "HS256",
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {"iat": now, "exp": now + exp_offset}
    if sub is not None:
        payload["sub"] = sub
    if iss is not None:
        payload["iss"] = iss
    if role is not None:
        payload["role"] = role
    payload["aud"] = aud
    return pyjwt.encode(payload, secret, algorithm=algorithm)


def _settings(
    *,
    auth_local_dev: bool = False,
    supabase_jwt_secret: str = _SECRET,
    supabase_url: str = _SUPABASE_URL,
    database_url: str = "postgresql+asyncpg://nosh:x@localhost:5432/nosh",
    app_environment: str = "local",
) -> Any:
    from app.config import AppEnvironment, Settings

    return Settings(
        auth_local_dev=auth_local_dev,
        supabase_jwt_secret=supabase_jwt_secret,
        supabase_url=supabase_url,
        database_url=database_url,
        app_environment=AppEnvironment(app_environment),
    )


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------


def test_local_dev_loopback_db_ok() -> None:
    for _host, url_host in (
        ("localhost", "localhost"),
        ("127.0.0.1", "127.0.0.1"),
        ("::1", "[::1]"),  # IPv6 requires brackets in URLs
    ):
        s = _settings(auth_local_dev=True, database_url=f"postgresql://x@{url_host}:5432/db")
        s.validate_auth_config()  # must not raise


def test_local_dev_0000_not_loopback() -> None:
    s = _settings(
        auth_local_dev=True,
        app_environment="local",
        database_url="postgresql://x@0.0.0.0:5432/db",
    )
    with pytest.raises(RuntimeError, match="non-loopback"):
        s.validate_auth_config()


def test_local_dev_dot_local_not_loopback() -> None:
    s = _settings(
        auth_local_dev=True,
        app_environment="local",
        database_url="postgresql://x@mydb.local:5432/db",
    )
    with pytest.raises(RuntimeError, match="non-loopback"):
        s.validate_auth_config()


def test_local_dev_remote_db_raises() -> None:
    s = _settings(
        auth_local_dev=True,
        app_environment="local",
        supabase_jwt_secret="",
        supabase_url="",
        database_url="postgresql://x@db.example.supabase.co:5432/postgres",
    )
    with pytest.raises(RuntimeError, match="non-loopback"):
        s.validate_auth_config()


def test_local_dev_production_env_raises() -> None:
    """auth_local_dev=True must be rejected when app_environment=production."""
    s = _settings(auth_local_dev=True, app_environment="production")
    with pytest.raises(RuntimeError, match="APP_ENVIRONMENT=local or test"):
        s.validate_auth_config()


def test_local_dev_test_env_loopback_ok() -> None:
    s = _settings(auth_local_dev=True, app_environment="test")
    s.validate_auth_config()


def test_production_no_url_raises() -> None:
    """Production mode requires SUPABASE_URL even when JWT secret is set."""
    s = _settings(auth_local_dev=False, supabase_jwt_secret="secret", supabase_url="")
    with pytest.raises(RuntimeError, match="SUPABASE_URL must be set"):
        s.validate_auth_config()


def test_production_no_credentials_raises() -> None:
    s = _settings(auth_local_dev=False, supabase_jwt_secret="", supabase_url="")
    with pytest.raises(RuntimeError, match="SUPABASE_URL must be set"):
        s.validate_auth_config()


def test_production_url_and_secret_ok() -> None:
    s = _settings(auth_local_dev=False, supabase_jwt_secret="secret", supabase_url=_SUPABASE_URL)
    s.validate_auth_config()  # must not raise


def test_production_url_only_ok() -> None:
    s = _settings(auth_local_dev=False, supabase_jwt_secret="", supabase_url=_SUPABASE_URL)
    s.validate_auth_config()  # RS256 path — must not raise


def test_supabase_url_trailing_slash_normalised() -> None:
    s = _settings(supabase_url="https://example.supabase.co/")
    assert s.normalised_supabase_url == "https://example.supabase.co"
    assert s.supabase_issuer == "https://example.supabase.co/auth/v1"


# ---------------------------------------------------------------------------
# HS256 token validation
# ---------------------------------------------------------------------------


def _decode_hs256(token: str) -> uuid.UUID:
    from app.auth.dependencies import _decode_hs256 as _fn

    return _fn(token, _SECRET, _ISSUER)


def test_valid_hs256_returns_uuid() -> None:
    assert _decode_hs256(_make_token()) == _USER_ID


def test_expired_token() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _decode_hs256(_make_token(exp_offset=-1))
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


def test_wrong_issuer() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _decode_hs256(_make_token(iss="https://evil.example.com/auth/v1"))
    assert exc.value.status_code == 401
    assert "issuer" in exc.value.detail.lower()


def test_missing_issuer() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _decode_hs256(_make_token(iss=None))
    assert exc.value.status_code == 401


def test_wrong_audience() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _decode_hs256(_make_token(aud="anon"))
    assert exc.value.status_code == 401
    assert "audience" in exc.value.detail.lower()


def test_wrong_role() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _decode_hs256(_make_token(role="anon"))
    assert exc.value.status_code == 403
    assert "role" in exc.value.detail.lower()


def test_missing_role() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _decode_hs256(_make_token(role=None))
    assert exc.value.status_code == 403


def test_missing_sub() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _decode_hs256(_make_token(sub=None))
    assert exc.value.status_code == 401


def test_non_uuid_sub() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _decode_hs256(_make_token(sub="not-a-uuid"))
    assert exc.value.status_code == 401
    assert "UUID" in exc.value.detail


def test_tampered_signature() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _decode_hs256(_make_token() + "tamper")
    assert exc.value.status_code == 401


def test_wrong_secret() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _decode_hs256(_make_token(secret="different-secret-must-be-long-enough"))
    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# JWKS / RS256 mocked tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_rs256_mocked() -> None:
    """RS256 token validated against a mocked signing key."""
    from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key

    # Generate a real RSA key pair for the test (no backend arg in modern cryptography).
    private_key = generate_private_key(public_exponent=65537, key_size=2048)
    token = pyjwt.encode(
        {
            "sub": str(_USER_ID),
            "iss": _ISSUER,
            "aud": "authenticated",
            "role": "authenticated",
            "exp": int(time.time()) + 3600,
        },
        private_key,
        algorithm="RS256",
    )

    mock_key = MagicMock()
    mock_key.key = private_key.public_key()

    from app.auth.dependencies import _decode_jwks

    with patch("app.auth.dependencies._get_jwks_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_key
        mock_client_fn.return_value = mock_client
        result = await _decode_jwks(token, "https://example.supabase.co/auth/v1/...", _ISSUER)

    assert result == _USER_ID


@pytest.mark.asyncio
async def test_unsupported_algorithm_rejected() -> None:
    """A token signed with an unsupported algorithm is rejected."""
    from fastapi import HTTPException

    # HS512 is not in the allowed JWKS algorithm set.
    token = _make_token(algorithm="HS512")

    mock_key = MagicMock()
    mock_key.key = _SECRET

    from app.auth.dependencies import _decode_jwks

    with patch("app.auth.dependencies._get_jwks_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_key
        mock_client_fn.return_value = mock_client
        with pytest.raises(HTTPException) as exc:
            await _decode_jwks(token, "https://...", _ISSUER)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_jwks_fetch_failure_returns_503() -> None:
    """JWKS network failures surface as 503, not 500."""
    from fastapi import HTTPException

    from app.auth.dependencies import _decode_jwks

    token = _make_token()

    with patch("app.auth.dependencies._get_jwks_client") as mock_client_fn:
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.side_effect = ConnectionError("timeout")
        mock_client_fn.return_value = mock_client
        with pytest.raises(HTTPException) as exc:
            await _decode_jwks(token, "https://...", _ISSUER)

    assert exc.value.status_code == 503


# ---------------------------------------------------------------------------
# Local dev adapter
# ---------------------------------------------------------------------------


def test_local_dev_accepts_uuid() -> None:
    from app.auth.dependencies import _validate_local_token

    uid = uuid.uuid4()
    assert _validate_local_token(str(uid)) == uid


def test_local_dev_rejects_non_uuid() -> None:
    from fastapi import HTTPException

    from app.auth.dependencies import _validate_local_token

    with pytest.raises(HTTPException) as exc:
        _validate_local_token("not-a-uuid")
    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# Route integration (no database)
# ---------------------------------------------------------------------------


def test_liveness_requires_no_auth(client: Any) -> None:
    resp = client.get("/health/live")
    assert resp.status_code == 200


def test_protected_endpoint_without_token_returns_4xx(client: Any) -> None:
    resp = client.get("/v1/me/meal-schedule")
    assert resp.status_code in (401, 403)


def test_protected_endpoint_with_local_dev_token_passes_auth(app: Any) -> None:
    from starlette.testclient import TestClient

    from app.schedules.schemas import MealScheduleResponse

    uid = uuid.UUID("00000000-0000-0000-0000-000000000001")
    empty = MealScheduleResponse(meals=[])
    with (
        patch("app.schedules.service.get_meal_schedule", AsyncMock(return_value=empty)),
        TestClient(app, raise_server_exceptions=False) as c,
    ):
        resp = c.get("/v1/me/meal-schedule", headers={"Authorization": f"Bearer {uid}"})

    assert resp.status_code not in (401, 403)
