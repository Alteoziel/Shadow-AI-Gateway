"""Layer D — API integration tests for gateway surfaces."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.main import app
from fastapi.testclient import TestClient
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_rejects_empty_body() -> None:
    response = client.post("/v1/chat/completions", json={}, headers=AUTH_HEADERS)
    assert response.status_code == 422


def test_chat_rejects_unauthenticated_empty_body() -> None:
    response = client.post("/v1/chat/completions", json={})
    assert response.status_code == 401


def test_chat_with_real_interceptor_and_mocked_provider() -> None:
    """Checkpoint #1 complete: valid bodies pass the interceptor into providers."""
    mock_provider = AsyncMock()
    mock_provider.chat_completion.return_value = {
        "id": "chatcmpl-int",
        "object": "chat.completion",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "world"},
                "finish_reason": "stop",
            }
        ],
    }

    with patch("app.api.v1.chat.OpenAIProvider", return_value=mock_provider):
        response = client.post(
            "/v1/chat/completions",
            headers=AUTH_HEADERS,
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "world"
    mock_provider.chat_completion.assert_awaited_once()
    forwarded = mock_provider.chat_completion.await_args.args[0]
    assert forwarded["correlation_id"]
    assert forwarded["received_at"]


def test_chat_with_mocked_interceptor_and_provider() -> None:
    normalized = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "hello"}],
    }
    mock_provider = AsyncMock()
    mock_provider.chat_completion.return_value = {
        "id": "chatcmpl-int",
        "object": "chat.completion",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "world"},
                "finish_reason": "stop",
            }
        ],
    }

    with (
        patch(
            "app.api.v1.chat.intercept_outbound_request",
            new=AsyncMock(return_value=normalized),
        ),
        patch("app.api.v1.chat.OpenAIProvider", return_value=mock_provider),
    ):
        response = client.post(
            "/v1/chat/completions",
            headers=AUTH_HEADERS,
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "world"


def test_extra_body_cannot_override_model() -> None:
    """Regression: Layer D contract — interceptor/model fields stay authoritative."""
    from app.api.v1.chat import _build_upstream_payload
    from app.models.schemas import ChatCompletionRequest, ChatMessage

    req = ChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[ChatMessage(role="user", content="hi")],
        extra_body={"model": "evil-model", "temperature": 0.2},
    )
    payload = _build_upstream_payload(
        req,
        {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert payload["model"] == "gpt-4o-mini"
    assert payload["temperature"] == 0.2
