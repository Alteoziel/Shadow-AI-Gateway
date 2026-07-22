from collections.abc import AsyncIterator, Awaitable, Callable
import os

import httpx
from fastapi.responses import StreamingResponse

_ALLOWED_RELAY_HEADERS = frozenset(
    {
        "content-type",
        "cache-control",
        "x-request-id",
        "x-openai-request-id",
        "openai-organization",
        "openai-processing-ms",
        "openai-version",
        "anthropic-ratelimit-requests-limit",
        "anthropic-ratelimit-requests-remaining",
        "anthropic-ratelimit-requests-reset",
        "anthropic-ratelimit-tokens-limit",
        "anthropic-ratelimit-tokens-remaining",
        "anthropic-ratelimit-tokens-reset",
        "request-id",
        "retry-after",
    }
)

# Soft cap on relayed bytes to bound slowloris-style streams (0 = unlimited).
_MAX_RELAY_BYTES = int(os.getenv("GATEWAY_MAX_STREAM_BYTES", str(25 * 1024 * 1024)))


async def relay_sse_stream(
    upstream: httpx.Response,
    *,
    media_type: str = "text/event-stream",
    on_complete: Callable[[], Awaitable[None]] | None = None,
) -> StreamingResponse:
    """Relay an upstream SSE/chunked body to the client without buffering.

    This helper is intentionally byte-preserving: OpenAI SSE and Anthropic
    Messages SSE are relayed as received. Provider-specific stream
    normalization must happen before this helper if a future phase adds it.

    Optional `on_complete` runs after the upstream body is fully consumed
    (or aborted) — use it to close provider HTTP clients without cutting
    the stream short.
    """

    async def _iter_chunks() -> AsyncIterator[bytes]:
        sent = 0
        try:
            async for chunk in upstream.aiter_bytes():
                sent += len(chunk)
                if _MAX_RELAY_BYTES > 0 and sent > _MAX_RELAY_BYTES:
                    break
                yield chunk
        finally:
            await upstream.aclose()
            if on_complete is not None:
                await on_complete()

    headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() in _ALLOWED_RELAY_HEADERS
    }

    return StreamingResponse(
        _iter_chunks(),
        status_code=upstream.status_code,
        media_type=media_type,
        headers=headers,
    )


async def iter_sse_lines(upstream: httpx.Response) -> AsyncIterator[str]:
    """Yield decoded SSE lines from an upstream streaming response."""
    async for line in upstream.aiter_lines():
        yield line
