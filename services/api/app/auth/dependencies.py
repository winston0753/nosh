"""JWT authentication for the Nosh FastAPI service.

Two modes
---------
LOCAL / TEST  (app_environment ∈ {local, test}, auth_local_dev=True):
    Bearer token = raw UUID string.  Only permitted when DATABASE_URL is
    a loopback address (localhost, 127.0.0.1, ::1).

PRODUCTION  (auth_local_dev=False):
    Validates a Supabase-issued JWT.  SUPABASE_URL is always required so
    the issuer can be compared to {SUPABASE_URL}/auth/v1.

    If SUPABASE_JWT_SECRET is also set, HS256 (legacy shared-secret) is
    used.  This is still valid for Supabase self-hosted and many cloud
    projects, but RS256 via JWKS is preferred for new projects.

    If SUPABASE_JWT_SECRET is empty, RS256 or ES256 via the project JWKS
    endpoint is used.  Supabase currently publishes RS256 keys but the
    specification allows EC keys.

    JWKS behaviour
    --------------
    - The JWK *set* (the full HTTPS response) is cached for JWKS_CACHE_TTL
      seconds (default 3600 s).  After expiry the set is re-fetched.
    - Individual key objects are NOT cached separately (cache_keys=False)
      so a revoked key cannot linger once the set expires.
    - The JWKS fetch is executed in a thread via anyio so it does not block
      the async event loop.
    - On encountering an unknown `kid`, PyJWKClient automatically re-fetches
      the set once (respecting a cooldown) before failing.

Validation always checks
------------------------
- Signature (HS256 secret or RS256/ES256 public key from JWKS).
- Expiry (exp, required claim).
- Issuer (iss, required claim, compared to {SUPABASE_URL}/auth/v1).
- Audience (aud == "authenticated").
- role claim == "authenticated".
- sub present and parseable as a UUID.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import anyio
import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWTError
from jwt.types import Options as JwtOptions

from app.config import get_settings

_bearer = HTTPBearer()

# ---------------------------------------------------------------------------
# JWKS cache lifetime.  Individual keys are NOT separately cached so a
# revoked key cannot survive past the next set expiry.
# ---------------------------------------------------------------------------
JWKS_CACHE_TTL: float = 3600.0  # seconds

# Module-level JWKS client; re-created if the URL changes.
_jwks_client: PyJWKClient | None = None
_jwks_client_url: str = ""


def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    global _jwks_client, _jwks_client_url
    if _jwks_client is None or _jwks_client_url != jwks_url:
        _jwks_client = PyJWKClient(
            jwks_url,
            cache_keys=False,  # Do NOT cache individual keys with unbounded TTL.
            cache_jwk_set=True,  # Cache the full JWK set for lifespan seconds.
            lifespan=JWKS_CACHE_TTL,
            # cooldown_duration: minimum seconds between re-fetches after a
            # known-kid miss.  Default (30 s) is acceptable.
        )
        _jwks_client_url = jwks_url
    return _jwks_client


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_local_token(token: str) -> uuid.UUID:
    """UUID-bypass adapter.  Never permitted outside local/test environments."""
    try:
        return uuid.UUID(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Local dev: Bearer token must be a valid UUID",
        ) from exc


def _extract_uuid_sub(payload: dict[str, Any]) -> uuid.UUID:
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing sub claim",
        )
    try:
        return uuid.UUID(str(sub))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subject claim: expected UUID",
        ) from exc


def _check_role(payload: dict[str, Any]) -> None:
    if payload.get("role") != "authenticated":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role: expected 'authenticated'",
        )


_DECODE_OPTS: JwtOptions = {
    "require": ["exp", "iss", "sub"],
    "verify_exp": True,
    "verify_aud": True,
    "verify_iss": True,  # Always verify issuer; SUPABASE_URL is required in production.
}


def _decode_common(token: str, key: Any, algorithms: list[str], issuer: str) -> uuid.UUID:
    """Shared decode/validate path for both HS256 and asymmetric modes."""
    try:
        payload = pyjwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience="authenticated",
            issuer=issuer,
            options=_DECODE_OPTS,
        )
    except pyjwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        ) from exc
    except pyjwt.InvalidIssuerError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid issuer: expected {issuer!r}",
        ) from exc
    except pyjwt.InvalidAudienceError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid audience: expected 'authenticated'",
        ) from exc
    except pyjwt.MissingRequiredClaimError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing required claim: {exc}",
        ) from exc
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token",
        ) from exc

    _check_role(payload)
    return _extract_uuid_sub(payload)


def _decode_hs256(token: str, secret: str, issuer: str) -> uuid.UUID:
    """HS256 legacy mode — still valid for Supabase projects that use the JWT Secret."""
    return _decode_common(token, secret, ["HS256"], issuer)


async def _decode_jwks(token: str, jwks_url: str, issuer: str) -> uuid.UUID:
    """Asymmetric mode — RS256 or ES256 via the project JWKS endpoint.

    The JWKS fetch runs in a thread so it does not block the async event loop.
    """
    client = _get_jwks_client(jwks_url)

    try:
        signing_key = await anyio.to_thread.run_sync(
            lambda: client.get_signing_key_from_jwt(token), abandon_on_cancel=True
        )
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to verify token signature",
        ) from exc
    except Exception as exc:
        # JWKS fetch failures (network, parse errors) must not leak internals.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc

    # Restrict to the algorithms Supabase publishes.  Never allow 'none' or
    # anything beyond the supported asymmetric set.
    return _decode_common(token, signing_key.key, ["RS256", "ES256"], issuer)


async def _validate_supabase_token(token: str) -> uuid.UUID:
    settings = get_settings()
    issuer = settings.supabase_issuer

    if not issuer:
        # Should have been caught at startup, but guard defensively.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not configured",
        )

    if settings.supabase_jwt_secret:
        # HS256 legacy mode: synchronous — no network call needed.
        return _decode_hs256(token, settings.supabase_jwt_secret, issuer)

    return await _decode_jwks(token, settings.supabase_jwks_url, issuer)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def _get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> uuid.UUID:
    settings = get_settings()
    token = credentials.credentials

    if settings.auth_local_dev:
        # UUID bypass — validate_auth_config() ensures this only activates
        # in local/test environments with a loopback DB.
        return _validate_local_token(token)

    return await _validate_supabase_token(token)


CurrentUser = Annotated[uuid.UUID, Depends(_get_current_user_id)]
