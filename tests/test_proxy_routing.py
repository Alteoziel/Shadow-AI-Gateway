from unittest.mock import AsyncMock, patch

import pytest
from app.main import app
from app.proxy.correlation import CORRELATION_ID_HEADER
from fastapi import HTTPException
from fastapi.testclient import TestClient
from tests.conftest import AUTH_HEADERS

client = TestClient(app)

CHAT_PAYLOAD = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "ping"}],
}


def test_chat_forwards_with_real_interceptor_and_mocked_provider():
    """Checkpoint #1 complete: real interceptor + provider adapter path."""
    mock_provider = AsyncMock()
    mock_provider.chat_completion.return_value = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "pong"},
                "finish_reason": "stop",
            }
        ],
    }

    with patch(
        "app.api.v1.chat.OpenAIProvider",
        return_value=mock_provider,
    ):
        response = client.post(
            "/v1/chat/completions",
            json=CHAT_PAYLOAD,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER].startswith("corr_")
    assert response.json()["choices"][0]["message"]["content"] == "pong"
    mock_provider.chat_completion.assert_awaited_once()
    forwarded = mock_provider.chat_completion.await_args.args[0]
    assert forwarded["model"] == "gpt-4o-mini"
    assert forwarded["messages"] == [{"role": "user", "content": "ping"}]
    assert "correlation_id" in forwarded
    assert "received_at" in forwarded
    mock_provider.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_forwards_to_provider_after_interceptor_implemented():
    """
    Documented unlock path: once intercept_outbound_request returns a payload,
    the route should delegate to the selected provider adapter.
    """
    normalized = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "ping"}],
    }
    mock_provider = AsyncMock()
    mock_interceptor = AsyncMock(return_value=normalized)
    mock_provider.chat_completion.return_value = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "pong"},
                "finish_reason": "stop",
            }
        ],
    }

    with (
        patch(
            "app.api.v1.chat.intercept_outbound_request",
            new=mock_interceptor,
        ),
        patch(
            "app.api.v1.chat.OpenAIProvider",
            return_value=mock_provider,
        ),
    ):
        response = client.post(
            "/v1/chat/completions",
            json=CHAT_PAYLOAD,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER].startswith("corr_")
    assert response.json()["choices"][0]["message"]["content"] == "pong"
    interceptor_kwargs = mock_interceptor.await_args.kwargs
    assert interceptor_kwargs["metadata"] == {"path": "/v1/chat/completions"}
    assert "correlation_id" not in interceptor_kwargs["metadata"]
    assert "received_at" not in interceptor_kwargs["metadata"]
    mock_provider.chat_completion.assert_awaited_once()
    mock_provider.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_returns_provider_gateway_errors_after_interceptor_implemented():
    """Provider reliability errors should surface as HTTP errors, not tracebacks."""
    normalized = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "ping"}],
    }
    mock_provider = AsyncMock()
    mock_provider.chat_completion.side_effect = HTTPException(
        status_code=502,
        detail={
            "error": "upstream_http_error",
            "provider": "openai",
            "upstream_status_code": 429,
            "message": "openai upstream returned HTTP 429",
        },
    )

    with (
        patch(
            "app.api.v1.chat.intercept_outbound_request",
            new=AsyncMock(return_value=normalized),
        ),
        patch(
            "app.api.v1.chat.OpenAIProvider",
            return_value=mock_provider,
        ),
    ):
        response = client.post(
            "/v1/chat/completions",
            json=CHAT_PAYLOAD,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 502
    assert response.json()["detail"]["error"] == "upstream_http_error"
    assert response.json()["detail"]["upstream_status_code"] == 429
    mock_provider.chat_completion.assert_awaited_once()
    mock_provider.aclose.assert_awaited_once()
