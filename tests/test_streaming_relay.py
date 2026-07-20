from unittest.mock import AsyncMock

import httpx
import pytest
from app.proxy.streaming import relay_sse_stream


@pytest.mark.asyncio
async def test_relay_sse_stream_yields_chunks_filters_headers_and_cleans_up():
    upstream = httpx.Response(
        202,
        content=b"data: one\n\ndata: two\n\n",
        headers={
            "content-length": "999",
            "transfer-encoding": "chunked",
            "connection": "keep-alive",
            "x-request-id": "req_123",
        },
    )
    on_complete = AsyncMock()

    response = await relay_sse_stream(upstream, on_complete=on_complete)
    body = b"".join([chunk async for chunk in response.body_iterator])

    assert body == b"data: one\n\ndata: two\n\n"
    assert response.status_code == 202
    assert response.media_type == "text/event-stream"
    assert response.headers["x-request-id"] == "req_123"
    assert "content-length" not in response.headers
    assert "transfer-encoding" not in response.headers
    assert "connection" not in response.headers
    assert upstream.is_closed
    on_complete.assert_awaited_once()
