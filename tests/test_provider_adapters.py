import json

import httpx
import pytest
import respx

from app.config import Settings
from app.proxy.payloads import to_anthropic_payload
from app.proxy.providers.anthropic import (
    ANTHROPIC_MESSAGES_URL,
    AnthropicProvider,
)
from app.proxy.providers.openai import OPENAI_CHAT_URL, OpenAIProvider


def _settings() -> Settings:
    return Settings(
        OPENAI_API_KEY="openai-test-key",
        ANTHROPIC_API_KEY="anthropic-test-key",
    )


def _request_json(route: respx.Route) -> dict:
    return json.loads(route.calls.last.request.content)


def test_anthropic_payload_maps_gateway_payload():
    payload = {
        "model": "claude-3-5-sonnet-latest",
        "messages": [
            {"role": "system", "content": "You are careful."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "tool", "content": "ignored"},
        ],
        "temperature": 0.1,
        "top_p": 0.8,
        "stop": "END",
    }

    anthropic_payload = to_anthropic_payload(payload)

    assert anthropic_payload == {
        "model": "claude-3-5-sonnet-latest",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ],
        "max_tokens": 1024,
        "system": "You are careful.",
        "temperature": 0.1,
        "top_p": 0.8,
        "stop_sequences": ["END"],
    }


def test_anthropic_response_converts_to_openai_shape():
    response = AnthropicProvider._to_openai_shape(
        {
            "id": "msg_123",
            "content": [
                {"type": "text", "text": "pong"},
                {"type": "thinking", "text": "ignored"},
            ],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 7},
        },
        model="claude-3-5-sonnet-latest",
    )

    assert response == {
        "id": "msg_123",
        "object": "chat.completion",
        "model": "claude-3-5-sonnet-latest",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "pong"},
                "finish_reason": "end_turn",
            }
        ],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 7,
            "total_tokens": 12,
        },
    }


@pytest.mark.asyncio
@respx.mock
async def test_openai_provider_posts_payload_with_auth_headers():
    route = respx.post(OPENAI_CHAT_URL).mock(
        return_value=httpx.Response(200, json={"id": "chatcmpl-test"})
    )
    provider = OpenAIProvider(_settings())
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "ping"}],
    }

    try:
        response = await provider.chat_completion(payload)
    finally:
        await provider.aclose()

    assert response == {"id": "chatcmpl-test"}
    assert route.called
    assert _request_json(route) == payload
    assert route.calls.last.request.headers["authorization"] == (
        "Bearer openai-test-key"
    )


@pytest.mark.asyncio
@respx.mock
async def test_anthropic_provider_posts_mapped_payload_and_returns_openai_shape():
    route = respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_123",
                "content": [{"type": "text", "text": "pong"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 3, "output_tokens": 4},
            },
        )
    )
    provider = AnthropicProvider(_settings())
    payload = {
        "model": "claude-3-5-sonnet-latest",
        "messages": [
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "ping"},
        ],
        "max_tokens": 64,
    }

    try:
        response = await provider.chat_completion(payload)
    finally:
        await provider.aclose()

    assert route.called
    assert _request_json(route) == {
        "model": "claude-3-5-sonnet-latest",
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 64,
        "system": "Be brief.",
    }
    assert route.calls.last.request.headers["x-api-key"] == "anthropic-test-key"
    assert response["choices"][0]["message"]["content"] == "pong"
    assert response["usage"]["total_tokens"] == 7


@pytest.mark.asyncio
@respx.mock
async def test_provider_streaming_requests_send_stream_true():
    openai_route = respx.post(OPENAI_CHAT_URL).mock(
        return_value=httpx.Response(200, content=b"data: openai\n\n")
    )
    anthropic_route = respx.post(ANTHROPIC_MESSAGES_URL).mock(
        return_value=httpx.Response(200, content=b"data: anthropic\n\n")
    )
    settings = _settings()
    openai = OpenAIProvider(settings)
    anthropic = AnthropicProvider(settings)

    try:
        openai_response = await openai.chat_completion_stream(
            {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "ping"}],
            }
        )
        anthropic_response = await anthropic.chat_completion_stream(
            {
                "model": "claude-3-5-sonnet-latest",
                "messages": [{"role": "user", "content": "ping"}],
            }
        )
    finally:
        await openai.aclose()
        await anthropic.aclose()

    await openai_response.aclose()
    await anthropic_response.aclose()

    assert _request_json(openai_route)["stream"] is True
    assert _request_json(anthropic_route)["stream"] is True
