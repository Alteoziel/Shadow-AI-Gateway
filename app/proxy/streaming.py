from collections.abc import AsyncIterator, Awaitable, Callable

import httpx
from fastapi.responses import StreamingResponse


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
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            if on_complete is not None:
                await on_complete()

    return StreamingResponse(
        _iter_chunks(),
        status_code=upstream.status_code,
        media_type=media_type,
        headers={
            key: value
            for key, value in upstream.headers.items()
            if key.lower() not in {"content-length", "transfer-encoding", "connection"}
        },
    )


async def iter_sse_lines(upstream: httpx.Response) -> AsyncIterator[str]:
    """Yield decoded SSE lines from an upstream streaming response."""
    async for line in upstream.aiter_lines():
        yield line
