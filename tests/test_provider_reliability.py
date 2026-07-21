import httpx
import pytest
from app.config import Settings
from app.proxy.providers.anthropic import AnthropicProvider
from app.proxy.providers.openai import OpenAIProvider
from fastapi import HTTPException

OPENAI_PAYLOAD = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "ping"}],
}

ANTHROPIC_PAYLOAD = {
    "model": "claude-3-5-haiku-latest",
    "messages": [{"role": "user", "content": "ping"}],
}


def _settings(*, openai_key: str = "sk-test", anthropic_key: str = "ak-test") -> Settings:
    return Settings(OPENAI_API_KEY=openai_key, ANTHROPIC_API_KEY=anthropic_key)


def _openai_provider(transport: httpx.MockTransport, *, key: str = "sk-test") -> OpenAIProvider:
    provider = OpenAIProvider(_settings(openai_key=key))
    provider._client = httpx.AsyncClient(transport=transport)
    return provider


def _anthropic_provider(
    transport: httpx.MockTransport,
    *,
    key: str = "ak-test",
) -> AnthropicProvider:
    provider = AnthropicProvider(_settings(anthropic_key=key))
    provider._client = httpx.AsyncClient(transport=transport)
    return provider


@pytest.mark.asyncio
async def test_openai_missing_api_key_raises_clear_gateway_error_before_request():
    called = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    provider = _openai_provider(httpx.MockTransport(handler), key="   ")

    with pytest.raises(HTTPException) as exc_info:
        await provider.chat_completion(OPENAI_PAYLOAD)

    await provider.aclose()
    assert called is False
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == {
        "error": "provider_configuration_error",
        "provider": "openai",
        "message": "openai API key is not configured",
    }


@pytest.mark.asyncio
async def test_openai_upstream_http_error_maps_to_gateway_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"}, request=request)

    provider = _openai_provider(httpx.MockTransport(handler))

    with pytest.raises(HTTPException) as exc_info:
        await provider.chat_completion(OPENAI_PAYLOAD)

    await provider.aclose()
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail["error"] == "upstream_http_error"
    assert exc_info.value.detail["provider"] == "openai"
    assert exc_info.value.detail["upstream_status_code"] == 429


@pytest.mark.asyncio
async def test_openai_timeout_maps_to_gateway_timeout():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow upstream", request=request)

    provider = _openai_provider(httpx.MockTransport(handler))

    with pytest.raises(HTTPException) as exc_info:
        await provider.chat_completion(OPENAI_PAYLOAD)

    await provider.aclose()
    assert exc_info.value.status_code == 504
    assert exc_info.value.detail == {
        "error": "upstream_timeout",
        "provider": "openai",
        "message": "openai upstream request timed out",
    }


@pytest.mark.asyncio
async def test_openai_request_error_maps_to_gateway_bad_gateway():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    provider = _openai_provider(httpx.MockTransport(handler))

    with pytest.raises(HTTPException) as exc_info:
        await provider.chat_completion(OPENAI_PAYLOAD)

    await provider.aclose()
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == {
        "error": "upstream_request_error",
        "provider": "openai",
        "message": "openai upstream request failed",
    }


@pytest.mark.asyncio
async def test_openai_streaming_status_error_maps_before_relay():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server error"}, request=request)

    provider = _openai_provider(httpx.MockTransport(handler))

    with pytest.raises(HTTPException) as exc_info:
        await provider.chat_completion_stream(OPENAI_PAYLOAD)

    await provider.aclose()
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail["error"] == "upstream_http_error"
    assert exc_info.value.detail["provider"] == "openai"
    assert exc_info.value.detail["upstream_status_code"] == 500


@pytest.mark.asyncio
async def test_anthropic_missing_api_key_raises_clear_gateway_error_before_request():
    called = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    provider = _anthropic_provider(httpx.MockTransport(handler), key="")

    with pytest.raises(HTTPException) as exc_info:
        await provider.chat_completion(ANTHROPIC_PAYLOAD)

    await provider.aclose()
    assert called is False
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == {
        "error": "provider_configuration_error",
        "provider": "anthropic",
        "message": "anthropic API key is not configured",
    }


@pytest.mark.asyncio
async def test_anthropic_upstream_http_error_maps_to_gateway_error():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"}, request=request)

    provider = _anthropic_provider(httpx.MockTransport(handler))

    with pytest.raises(HTTPException) as exc_info:
        await provider.chat_completion(ANTHROPIC_PAYLOAD)

    await provider.aclose()
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail["error"] == "upstream_http_error"
    assert exc_info.value.detail["provider"] == "anthropic"
    assert exc_info.value.detail["upstream_status_code"] == 400


@pytest.mark.asyncio
async def test_anthropic_timeout_maps_to_gateway_timeout():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow connect", request=request)

    provider = _anthropic_provider(httpx.MockTransport(handler))

    with pytest.raises(HTTPException) as exc_info:
        await provider.chat_completion(ANTHROPIC_PAYLOAD)

    await provider.aclose()
    assert exc_info.value.status_code == 504
    assert exc_info.value.detail == {
        "error": "upstream_timeout",
        "provider": "anthropic",
        "message": "anthropic upstream request timed out",
    }


@pytest.mark.asyncio
async def test_anthropic_request_error_maps_to_gateway_bad_gateway():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.NetworkError("network failed", request=request)

    provider = _anthropic_provider(httpx.MockTransport(handler))

    with pytest.raises(HTTPException) as exc_info:
        await provider.chat_completion(ANTHROPIC_PAYLOAD)

    await provider.aclose()
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == {
        "error": "upstream_request_error",
        "provider": "anthropic",
        "message": "anthropic upstream request failed",
    }


@pytest.mark.asyncio
async def test_anthropic_streaming_status_error_maps_before_raw_relay():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"}, request=request)

    provider = _anthropic_provider(httpx.MockTransport(handler))

    with pytest.raises(HTTPException) as exc_info:
        await provider.chat_completion_stream(ANTHROPIC_PAYLOAD)

    await provider.aclose()
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail["error"] == "upstream_http_error"
    assert exc_info.value.detail["provider"] == "anthropic"
    assert exc_info.value.detail["upstream_status_code"] == 503


@pytest.mark.asyncio
async def test_anthropic_streaming_success_returns_raw_upstream_response():
    raw_sse = b'event: content_block_delta\ndata: {"type":"content_block_delta"}\n\n'

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=raw_sse,
            headers={"content-type": "text/event-stream"},
            request=request,
        )

    provider = _anthropic_provider(httpx.MockTransport(handler))
    response = await provider.chat_completion_stream(ANTHROPIC_PAYLOAD)

    try:
        assert response.status_code == 200
        assert await response.aread() == raw_sse
    finally:
        await response.aclose()
        await provider.aclose()
