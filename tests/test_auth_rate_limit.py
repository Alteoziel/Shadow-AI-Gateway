"""Auth + rate-limit coverage for POST /v1/chat/completions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.config import clear_settings_cache
from app.main import app
from app.security.audit import AuditEventType, get_audit_sink
from app.security.rate_limit import reset_rate_limit_state
from fastapi.testclient import TestClient
from tests.conftest import AUTH_HEADERS, TEST_GATEWAY_API_KEY

client = TestClient(app)

CHAT_PAYLOAD = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "ping"}],
}

PROVIDER_RESPONSE = {
    "id": "chatcmpl-auth",
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


def _mock_openai_provider() -> AsyncMock:
    mock_provider = AsyncMock()
    mock_provider.chat_completion.return_value = PROVIDER_RESPONSE
    return mock_provider


def test_chat_401_without_credentials() -> None:
    response = client.post("/v1/chat/completions", json=CHAT_PAYLOAD)
    assert response.status_code == 401


def test_chat_401_with_wrong_key() -> None:
    response = client.post(
        "/v1/chat/completions",
        json=CHAT_PAYLOAD,
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401


def test_chat_200_with_valid_bearer() -> None:
    mock_provider = _mock_openai_provider()
    with patch("app.api.v1.chat.OpenAIProvider", return_value=mock_provider):
        response = client.post(
            "/v1/chat/completions",
            json=CHAT_PAYLOAD,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "pong"
    mock_provider.chat_completion.assert_awaited_once()


def test_chat_200_with_valid_x_api_key() -> None:
    mock_provider = _mock_openai_provider()
    with patch("app.api.v1.chat.OpenAIProvider", return_value=mock_provider):
        response = client.post(
            "/v1/chat/completions",
            json=CHAT_PAYLOAD,
            headers={"X-API-Key": TEST_GATEWAY_API_KEY},
        )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "pong"


def test_chat_429_when_rate_limit_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEWAY_RATE_LIMIT_PER_MINUTE", "2")
    clear_settings_cache()
    reset_rate_limit_state()

    mock_provider = _mock_openai_provider()
    with patch("app.api.v1.chat.OpenAIProvider", return_value=mock_provider):
        first = client.post(
            "/v1/chat/completions",
            json=CHAT_PAYLOAD,
            headers=AUTH_HEADERS,
        )
        second = client.post(
            "/v1/chat/completions",
            json=CHAT_PAYLOAD,
            headers=AUTH_HEADERS,
        )
        third = client.post(
            "/v1/chat/completions",
            json=CHAT_PAYLOAD,
            headers=AUTH_HEADERS,
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert "Rate limit exceeded" in third.json()["detail"]


def test_audit_sink_records_request_received_and_auth_ok() -> None:
    mock_provider = _mock_openai_provider()
    with patch("app.api.v1.chat.OpenAIProvider", return_value=mock_provider):
        response = client.post(
            "/v1/chat/completions",
            json=CHAT_PAYLOAD,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    event_types = [event.event_type for event in get_audit_sink().events]
    assert AuditEventType.REQUEST_RECEIVED in event_types
    assert AuditEventType.AUTH_OK in event_types
