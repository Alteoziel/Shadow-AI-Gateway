import ast
import inspect
from pathlib import Path

import pytest

from app.proxy.interceptor import intercept_outbound_request


def test_intercept_outbound_request_exists_and_is_async():
    assert callable(intercept_outbound_request)
    assert inspect.iscoroutinefunction(intercept_outbound_request)


@pytest.mark.asyncio
async def test_intercept_outbound_request_raises_not_implemented():
    with pytest.raises(NotImplementedError) as exc_info:
        await intercept_outbound_request(body={"model": "gpt-4o-mini", "messages": []})
    assert "Checkpoint #1" in str(exc_info.value)


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
