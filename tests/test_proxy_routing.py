from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CHAT_PAYLOAD = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "ping"}],
}


def test_chat_returns_501_while_interceptor_not_implemented():
    """Full provider routing unlocks after human fills Checkpoint #1."""
    response = client.post("/v1/chat/completions", json=CHAT_PAYLOAD)
    assert response.status_code == 501
    detail = response.json()["detail"]
    assert "Checkpoint #1" in detail
    assert "intercept_outbound_request" in detail


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
            new=AsyncMock(return_value=normalized),
        ),
        patch(
            "app.api.v1.chat.OpenAIProvider",
            return_value=mock_provider,
        ),
    ):
        response = client.post("/v1/chat/completions", json=CHAT_PAYLOAD)

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "pong"
    mock_provider.chat_completion.assert_awaited_once()
    mock_provider.aclose.assert_awaited_once()
