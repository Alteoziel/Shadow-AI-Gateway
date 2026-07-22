"""Gateway caller authentication (Bearer / X-API-Key).

Protects /v1 routes from becoming an open relay. Health stays public.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


def _configured_keys(settings: Settings) -> frozenset[str]:
    keys: set[str] = set()
    if settings.gateway_api_key.strip():
        keys.add(settings.gateway_api_key.strip())
    for part in settings.gateway_api_keys.split(","):
        cleaned = part.strip()
        if cleaned:
            keys.add(cleaned)
    return frozenset(keys)


def key_fingerprint(token: str) -> str:
    """Short opaque id for audit / rate-limit buckets (not password storage)."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        token.encode("utf-8"),
        salt=b"shadow-ai-gateway-key-id-v1",
        iterations=10_000,
        dklen=8,
    ).hex()


def _constant_time_match(provided: str, allowed: frozenset[str]) -> bool:
    return any(hmac.compare_digest(provided, key) for key in allowed)


async def require_gateway_auth(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer),
    ] = None,
) -> str:
    """Require a valid gateway API key. Returns a fingerprint for auditing."""
    allowed = _configured_keys(settings)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Gateway auth is not configured. Set GATEWAY_API_KEY (or "
                "GATEWAY_API_KEYS) before serving /v1 traffic."
            ),
        )

    token: str | None = None
    if credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    else:
        header_key = request.headers.get("x-api-key")
        if header_key:
            token = header_key.strip()

    if not token or not _constant_time_match(token, allowed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing gateway API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    fingerprint = key_fingerprint(token)
    request.state.gateway_key_id = fingerprint
    return fingerprint
