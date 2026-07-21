import ast
import inspect
from datetime import datetime
from pathlib import Path

import pytest
from app.proxy.correlation import CORRELATION_ID_HEADER
from app.proxy.interceptor import intercept_outbound_request
from fastapi import HTTPException


def test_intercept_outbound_request_exists_and_is_async():
    assert callable(intercept_outbound_request)
    assert inspect.iscoroutinefunction(intercept_outbound_request)


@pytest.mark.asyncio
async def test_intercept_outbound_request_normalizes_valid_payload():
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "ping"}],
        "stream": False,
    }

    normalized = await intercept_outbound_request(
        body=body,
        headers={CORRELATION_ID_HEADER: "client-corr-1"},
    )

    assert normalized is not body
    assert normalized["model"] == "gpt-4o-mini"
    assert normalized["messages"] == [{"role": "user", "content": "ping"}]
    assert normalized["correlation_id"] == "client-corr-1"
    assert datetime.fromisoformat(normalized["received_at"]).tzinfo is not None


@pytest.mark.asyncio
async def test_intercept_outbound_request_rejects_empty_messages():
    with pytest.raises(HTTPException) as exc_info:
        await intercept_outbound_request(
            body={"model": "gpt-4o-mini", "messages": []},
        )

    assert exc_info.value.status_code == 400
    assert "messages" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_intercept_outbound_request_rejects_missing_model():
    with pytest.raises(HTTPException) as exc_info:
        await intercept_outbound_request(
            body={"messages": [{"role": "user", "content": "hi"}]},
        )

    assert exc_info.value.status_code == 400
    assert "model" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_intercept_outbound_request_rejects_incomplete_message():
    with pytest.raises(HTTPException) as exc_info:
        await intercept_outbound_request(
            body={
                "model": "gpt-4o-mini",
                "messages": [{"content": "missing role"}],
            },
        )

    assert exc_info.value.status_code == 400
    assert "role" in str(exc_info.value.detail).lower()


def test_intercept_outbound_request_no_longer_raises_not_implemented():
    source = inspect.getsource(intercept_outbound_request)

    assert "raise NotImplementedError" not in source
    assert "HTTPException" in source


def test_chat_route_calls_interceptor_before_provider():
    chat_path = Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "chat.py"
    source = chat_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert "intercept_outbound_request" in source

    call_names: list[str] = []
    provider_hints = ("OpenAIProvider", "AnthropicProvider", "chat_completion")

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            call_names.append(node.func.id)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            call_names.append(node.func.attr)

    assert "intercept_outbound_request" in call_names

    interceptor_index = source.index("intercept_outbound_request")
    # First provider-related usage should appear after interceptor call
    first_provider_index = min(
        source.index(hint) for hint in provider_hints if hint in source
    )
    assert interceptor_index < first_provider_index
