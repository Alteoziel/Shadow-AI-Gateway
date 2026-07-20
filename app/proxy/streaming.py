from collections.abc import AsyncIterator

import httpx
from fastapi.responses import StreamingResponse


async def relay_sse_stream(
    upstream: httpx.Response,
    *,
    media_type: str = "text/event-stream",
) -> StreamingResponse:
    """Relay an upstream SSE/chunked body to the client without buffering."""

    async def _iter_chunks() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()

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
