from app.api.v1.chat import _build_upstream_payload, _resolve_provider
from app.config import get_settings
from app.models.schemas import ChatCompletionRequest


def _chat_request(**overrides):
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "ping"}],
    }
    payload.update(overrides)
    return ChatCompletionRequest(**payload)


def test_resolve_provider_uses_request_override(monkeypatch):
    monkeypatch.setenv("DEFAULT_PROVIDER", "openai")
    get_settings.cache_clear()

    request = _chat_request(provider="anthropic")

    try:
        assert _resolve_provider(request) == "anthropic"
    finally:
        get_settings.cache_clear()


def test_resolve_provider_uses_default_provider_env(monkeypatch):
    monkeypatch.setenv("DEFAULT_PROVIDER", "anthropic")
    get_settings.cache_clear()

    request = _chat_request()

    try:
        assert _resolve_provider(request) == "anthropic"
    finally:
        get_settings.cache_clear()


def test_build_upstream_payload_protects_interceptor_fields():
    request = _chat_request(
        stream=True,
        temperature=0.2,
        max_tokens=128,
        top_p=0.9,
        stop=["END"],
        extra_body={
            "model": "should-not-win",
            "messages": [{"role": "user", "content": "should-not-win"}],
            "stream": False,
            "metadata": {"tenant": "acme"},
        },
    )
    normalized = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "normalized"}],
        "stream": False,
        "correlation_id": "corr-123",
    }

    payload = _build_upstream_payload(request, normalized)

    assert payload == {
        "metadata": {"tenant": "acme"},
        "temperature": 0.2,
        "max_tokens": 128,
        "top_p": 0.9,
        "stop": ["END"],
        "correlation_id": "corr-123",
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "normalized"}],
        "stream": True,
    }
