from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_chat_uses_request_provider_after_interceptor_implemented():
    """Unlock path honors request-level provider selection after Checkpoint #1."""
    normalized = {
        "model": "claude-3-5-sonnet-latest",
        "messages": [{"role": "user", "content": "ping"}],
    }
    mock_provider = AsyncMock()
    mock_provider.chat_completion.return_value = {
        "id": "msg-test",
        "object": "chat.completion",
        "model": "claude-3-5-sonnet-latest",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "pong"},
                "finish_reason": "end_turn",
            }
        ],
    }

    with (
        patch(
            "app.api.v1.chat.intercept_outbound_request",
            new=AsyncMock(return_value=normalized),
        ),
        patch(
            "app.api.v1.chat.AnthropicProvider",
            return_value=mock_provider,
        ) as mock_anthropic_provider,
    ):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "claude-3-5-sonnet-latest",
                "messages": [{"role": "user", "content": "ping"}],
                "provider": "anthropic",
            },
        )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "pong"
    mock_anthropic_provider.assert_called_once()
    mock_provider.chat_completion.assert_awaited_once()
    mock_provider.aclose.assert_awaited_once()
