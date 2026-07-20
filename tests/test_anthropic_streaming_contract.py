import httpx
import pytest

from app.proxy.streaming import relay_sse_stream


@pytest.mark.asyncio
async def test_relay_sse_stream_preserves_raw_anthropic_sse_bytes():
    raw_sse = (
        b"event: message_start\n"
        b'data: {"type":"message_start","message":{"id":"msg_123"}}\n\n'
        b"event: content_block_delta\n"
        b'data: {"type":"content_block_delta","delta":{"text":"hello"}}\n\n'
    )
    upstream = httpx.Response(
        200,
        content=raw_sse,
        headers={"content-type": "text/event-stream"},
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
    )

    response = await relay_sse_stream(upstream)
    body = b"".join([chunk async for chunk in response.body_iterator])

    assert response.status_code == 200
    assert body == raw_sse
