"""Streaming relay failure / cleanup paths."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import httpx
import pytest
from app.proxy.streaming import relay_sse_stream


@pytest.mark.asyncio
async def test_relay_sse_mid_stream_exception_still_cleans_up() -> None:
    upstream = AsyncMock(spec=httpx.Response)
    upstream.status_code = 200
    upstream.headers = httpx.Headers({"x-request-id": "req_mid"})
    upstream.is_closed = False

    async def boom_bytes() -> AsyncIterator[bytes]:
        yield b"data: first\n\n"
        raise RuntimeError("upstream broke")

    async def aclose() -> None:
        upstream.is_closed = True

    upstream.aiter_bytes = boom_bytes
    upstream.aclose = AsyncMock(side_effect=aclose)
    on_complete = AsyncMock()

    response = await relay_sse_stream(upstream, on_complete=on_complete)
    chunks: list[bytes] = []
    with pytest.raises(RuntimeError, match="upstream broke"):
        async for chunk in response.body_iterator:
            chunks.append(chunk)

    assert chunks == [b"data: first\n\n"]
    on_complete.assert_awaited_once()
    upstream.aclose.assert_awaited_once()
    assert upstream.is_closed


@pytest.mark.asyncio
async def test_relay_sse_empty_stream_still_cleans_up() -> None:
    upstream = httpx.Response(
        200,
        content=b"",
        headers={"x-request-id": "req_empty"},
    )
    on_complete = AsyncMock()

    response = await relay_sse_stream(upstream, on_complete=on_complete)
    body = b"".join([chunk async for chunk in response.body_iterator])

    assert body == b""
    assert upstream.is_closed
    on_complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_relay_sse_malformed_bytes_relayed_as_is_then_cleanup() -> None:
    malformed = b"data: incomplete\ndata: still-partial"
    upstream = httpx.Response(
        200,
        content=malformed,
        headers={"x-request-id": "req_partial"},
    )
    on_complete = AsyncMock()

    response = await relay_sse_stream(upstream, on_complete=on_complete)
    body = b"".join([chunk async for chunk in response.body_iterator])

    assert body == malformed
    assert upstream.is_closed
    on_complete.assert_awaited_once()
