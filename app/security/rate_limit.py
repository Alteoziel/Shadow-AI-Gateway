"""In-memory per-caller rate limiting for /v1 routes."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.config import Settings, get_settings
from app.security.auth import require_gateway_auth

_lock = Lock()
_buckets: dict[str, deque[float]] = defaultdict(deque)


def reset_rate_limit_state() -> None:
    """Test helper — clear all buckets."""
    with _lock:
        _buckets.clear()


def _prune(window: deque[float], now: float, window_seconds: float) -> None:
    cutoff = now - window_seconds
    while window and window[0] < cutoff:
        window.popleft()


async def enforce_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    key_id: Annotated[str, Depends(require_gateway_auth)],
) -> str:
    """Sliding-window rate limit keyed by authenticated gateway key fingerprint."""
    limit = settings.gateway_rate_limit_per_minute
    if limit <= 0:
        return key_id

    window_seconds = 60.0
    bucket_key = f"key:{key_id}"
    now = time.monotonic()

    with _lock:
        window = _buckets[bucket_key]
        _prune(window, now, window_seconds)
        if len(window) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({limit} requests per minute)",
                headers={"Retry-After": "60"},
            )
        window.append(now)

    request.state.rate_limit_key = bucket_key
    return key_id
