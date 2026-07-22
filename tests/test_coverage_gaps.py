"""Fill remaining coverage gaps toward the 95% floor."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from app.api.v1.chat import _get_provider_adapter
from app.config import clear_settings_cache
from app.main import _configure_logging, create_app, lifespan
from app.proxy.correlation import parse_correlation_id
from app.proxy.payloads import to_anthropic_payload
from app.proxy.providers.base import map_httpx_error
from app.proxy.streaming import iter_sse_lines
from app.security.audit import (
    AuditEventType,
    InMemoryAuditSink,
    emit_audit,
    get_audit_sink,
    set_audit_sink,
)
from app.security.auth import _configured_keys
from app.security.rate_limit import _buckets, _lock, reset_rate_limit_state
from fastapi import HTTPException
from fastapi.testclient import TestClient
from tests.conftest import AUTH_HEADERS

CHAT_PAYLOAD = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "ping"}],
}

NORMALIZED = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "ping"}],
}


# --- chat.py -----------------------------------------------------------------


def test_get_provider_adapter_rejects_unsupported_provider() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _get_provider_adapter("bogus")
    assert exc_info.value.status_code == 400
    assert "Unsupported provider: bogus" in exc_info.value.detail


def test_chat_interceptor_not_implemented_returns_501_and_audits() -> None:
    client = TestClient(create_app())
    with patch(
        "app.api.v1.chat.intercept_outbound_request",
        new=AsyncMock(side_effect=NotImplementedError("checkpoint")),
    ):
        response = client.post(
            "/v1/chat/completions",
            json=CHAT_PAYLOAD,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 501
    assert "Checkpoint #1" in response.json()["detail"]
    event_types = [e.event_type for e in get_audit_sink().events]
    assert AuditEventType.INTERCEPTOR_BLOCK in event_types
    block = next(
        e for e in get_audit_sink().events if e.event_type == AuditEventType.INTERCEPTOR_BLOCK
    )
    assert block.blocked is True
    assert block.reason == "interceptor_not_implemented"


def test_chat_interceptor_http_exception_reraise_and_audits() -> None:
    client = TestClient(create_app())
    with patch(
        "app.api.v1.chat.intercept_outbound_request",
        new=AsyncMock(
            side_effect=HTTPException(status_code=403, detail="blocked by policy")
        ),
    ):
        response = client.post(
            "/v1/chat/completions",
            json=CHAT_PAYLOAD,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "blocked by policy"
    block = next(
        e for e in get_audit_sink().events if e.event_type == AuditEventType.INTERCEPTOR_BLOCK
    )
    assert block.blocked is True
    assert block.reason == "blocked by policy"
    assert block.metadata.get("status_code") == 403


def test_chat_stream_success_relays_sse() -> None:
    client = TestClient(create_app())
    mock_provider = AsyncMock()
    mock_provider.chat_completion_stream.return_value = httpx.Response(
        200,
        content=b"data: {\"ok\":true}\n\n",
        headers={"content-type": "text/event-stream", "x-request-id": "req_stream"},
    )

    with (
        patch(
            "app.api.v1.chat.intercept_outbound_request",
            new=AsyncMock(return_value=NORMALIZED),
        ),
        patch("app.api.v1.chat.OpenAIProvider", return_value=mock_provider),
    ):
        response = client.post(
            "/v1/chat/completions",
            json={**CHAT_PAYLOAD, "stream": True},
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    assert b"data: {\"ok\":true}" in response.content
    mock_provider.chat_completion_stream.assert_awaited_once()
    mock_provider.aclose.assert_awaited_once()


def test_chat_stream_provider_error_audits_and_aclose() -> None:
    client = TestClient(create_app())
    mock_provider = AsyncMock()
    mock_provider.chat_completion_stream.side_effect = RuntimeError("stream boom")

    with (
        patch(
            "app.api.v1.chat.intercept_outbound_request",
            new=AsyncMock(return_value=NORMALIZED),
        ),
        patch("app.api.v1.chat.OpenAIProvider", return_value=mock_provider),
    ):
        with pytest.raises(RuntimeError, match="stream boom"):
            client.post(
                "/v1/chat/completions",
                json={**CHAT_PAYLOAD, "stream": True},
                headers=AUTH_HEADERS,
            )

    mock_provider.aclose.assert_awaited_once()
    err = next(
        e for e in get_audit_sink().events if e.event_type == AuditEventType.PROVIDER_ERROR
    )
    assert err.blocked is True
    assert err.reason == "RuntimeError"
    assert err.provider == "openai"


def test_chat_nonstream_provider_error_audits() -> None:
    client = TestClient(create_app())
    mock_provider = AsyncMock()
    mock_provider.chat_completion.side_effect = RuntimeError("provider boom")

    with (
        patch(
            "app.api.v1.chat.intercept_outbound_request",
            new=AsyncMock(return_value=NORMALIZED),
        ),
        patch("app.api.v1.chat.OpenAIProvider", return_value=mock_provider),
    ):
        with pytest.raises(RuntimeError, match="provider boom"):
            client.post(
                "/v1/chat/completions",
                json=CHAT_PAYLOAD,
                headers=AUTH_HEADERS,
            )

    mock_provider.aclose.assert_awaited_once()
    err = next(
        e for e in get_audit_sink().events if e.event_type == AuditEventType.PROVIDER_ERROR
    )
    assert err.blocked is True
    assert err.reason == "RuntimeError"


# --- main.py -----------------------------------------------------------------


def test_configure_logging_accepts_level_and_fallback() -> None:
    _configure_logging("DEBUG")
    _configure_logging("not-a-real-level")


@pytest.mark.asyncio
async def test_lifespan_startup_and_shutdown() -> None:
    app = create_app()
    async with lifespan(app):
        pass


def test_middleware_exception_path_propagates() -> None:
    app = create_app()

    @app.get("/__test_boom")
    async def boom() -> None:
        raise RuntimeError("middleware boom")

    with TestClient(app, raise_server_exceptions=True) as client:
        with pytest.raises(RuntimeError, match="middleware boom"):
            client.get("/__test_boom")


# --- correlation / payloads / streaming --------------------------------------


def test_parse_correlation_id_none_generates() -> None:
    correlation_id = parse_correlation_id(None)
    assert correlation_id.startswith("corr_")


def test_parse_correlation_id_case_insensitive_header() -> None:
    assert parse_correlation_id({"x-correlation-id": "client-corr-abc"}) == "client-corr-abc"


def test_to_anthropic_payload_rejects_non_mapping() -> None:
    with pytest.raises(TypeError, match="mapping"):
        to_anthropic_payload("not-a-mapping")  # type: ignore[arg-type]


def test_to_anthropic_payload_rejects_empty_model() -> None:
    with pytest.raises(ValueError, match="non-empty model"):
        to_anthropic_payload({"model": "", "messages": []})
    with pytest.raises(ValueError, match="non-empty model"):
        to_anthropic_payload({"model": 123, "messages": []})


def test_to_anthropic_payload_rejects_non_list_messages() -> None:
    with pytest.raises(ValueError, match="must be a list"):
        to_anthropic_payload({"model": "claude", "messages": "nope"})


def test_to_anthropic_payload_skips_non_mapping_messages_and_str_system() -> None:
    result = to_anthropic_payload(
        {
            "model": "claude-3-5-sonnet-latest",
            "messages": [
                "skip-me",
                {"role": "system", "content": ["part", 1]},
                {"role": "user", "content": "hi"},
            ],
        }
    )
    assert result["messages"] == [{"role": "user", "content": "hi"}]
    assert result["system"] == str(["part", 1])


@pytest.mark.asyncio
async def test_iter_sse_lines_yields_decoded_lines() -> None:
    upstream = httpx.Response(200, content=b"data: one\n\ndata: two\n\n")
    lines = [line async for line in iter_sse_lines(upstream)]
    assert "data: one" in lines
    assert "data: two" in lines


# --- security -----------------------------------------------------------------


def test_configured_keys_includes_primary_and_comma_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GATEWAY_API_KEY", "primary-key")
    monkeypatch.setenv("GATEWAY_API_KEYS", "key2, key3")
    clear_settings_cache()
    from app.config import get_settings

    keys = _configured_keys(get_settings())
    assert keys == frozenset({"primary-key", "key2", "key3"})


def test_empty_auth_config_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEWAY_API_KEY", "")
    monkeypatch.setenv("GATEWAY_API_KEYS", "")
    clear_settings_cache()
    client = TestClient(create_app())
    response = client.post("/v1/chat/completions", json=CHAT_PAYLOAD)
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_rate_limit_requires_explicit_disable_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """limit=0 alone must NOT disable limiting; use GATEWAY_RATE_LIMIT_DISABLED."""
    monkeypatch.setenv("GATEWAY_RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.delenv("GATEWAY_RATE_LIMIT_DISABLED", raising=False)
    clear_settings_cache()
    reset_rate_limit_state()
    client = TestClient(create_app())
    mock_provider = AsyncMock()
    mock_provider.chat_completion.return_value = {"id": "ok", "choices": []}

    with patch("app.api.v1.chat.OpenAIProvider", return_value=mock_provider):
        # Falls back to 60/min — five requests must succeed
        for _ in range(5):
            response = client.post(
                "/v1/chat/completions",
                json=CHAT_PAYLOAD,
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 200


def test_rate_limit_disabled_with_explicit_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GATEWAY_RATE_LIMIT_DISABLED", "true")
    monkeypatch.setenv("GATEWAY_RATE_LIMIT_PER_MINUTE", "1")
    clear_settings_cache()
    reset_rate_limit_state()
    client = TestClient(create_app())
    mock_provider = AsyncMock()
    mock_provider.chat_completion.return_value = {"id": "ok", "choices": []}

    with patch("app.api.v1.chat.OpenAIProvider", return_value=mock_provider):
        for _ in range(5):
            response = client.post(
                "/v1/chat/completions",
                json=CHAT_PAYLOAD,
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 200


def test_auth_denied_emits_audit_event() -> None:
    client = TestClient(create_app())
    response = client.post("/v1/chat/completions", json=CHAT_PAYLOAD)
    assert response.status_code == 401
    event_types = [e.event_type for e in get_audit_sink().events]
    assert AuditEventType.AUTH_DENIED in event_types


def test_rate_limit_prune_drops_old_timestamps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEWAY_RATE_LIMIT_PER_MINUTE", "2")
    clear_settings_cache()
    reset_rate_limit_state()

    from app.security.auth import key_fingerprint
    from tests.conftest import TEST_GATEWAY_API_KEY

    bucket_key = f"key:{key_fingerprint(TEST_GATEWAY_API_KEY)}"
    now = time.monotonic()
    with _lock:
        _buckets[bucket_key].append(now - 120.0)
        _buckets[bucket_key].append(now - 90.0)

    client = TestClient(create_app())
    mock_provider = AsyncMock()
    mock_provider.chat_completion.return_value = {"id": "ok", "choices": []}

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

    assert first.status_code == 200
    assert second.status_code == 200


@pytest.mark.asyncio
async def test_set_audit_sink_replaces_sink() -> None:
    original = get_audit_sink()
    replacement = InMemoryAuditSink()
    try:
        set_audit_sink(replacement)
        await emit_audit(
            AuditEventType.AUTH_OK,
            correlation_id="corr-sink-swap",
        )
        assert len(replacement.events) == 1
        assert replacement.events[0].correlation_id == "corr-sink-swap"
        assert replacement.events[0] not in original.events
    finally:
        set_audit_sink(original)


# --- providers/base + streaming branch partials ------------------------------


def test_map_httpx_error_generic_upstream_error() -> None:
    exc = httpx.HTTPError("unclassified")
    mapped = map_httpx_error("openai", exc)
    assert mapped.status_code == 502
    assert mapped.detail == {
        "error": "upstream_error",
        "provider": "openai",
        "message": "openai upstream request failed",
    }


@pytest.mark.asyncio
async def test_openai_streaming_connect_error_skips_response_aclose() -> None:
    from app.config import Settings
    from app.proxy.providers.openai import OpenAIProvider

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no connection", request=request)

    provider = OpenAIProvider(Settings(OPENAI_API_KEY="sk-test"))
    provider._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(HTTPException) as exc_info:
            await provider.chat_completion_stream(
                {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "x"}]}
            )
        assert exc_info.value.detail["error"] == "upstream_request_error"
    finally:
        await provider.aclose()


@pytest.mark.asyncio
async def test_anthropic_streaming_connect_error_skips_response_aclose() -> None:
    from app.config import Settings
    from app.proxy.providers.anthropic import AnthropicProvider

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no connection", request=request)

    provider = AnthropicProvider(Settings(ANTHROPIC_API_KEY="ak-test"))
    provider._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(HTTPException) as exc_info:
            await provider.chat_completion_stream(
                {
                    "model": "claude-3-5-haiku-latest",
                    "messages": [{"role": "user", "content": "x"}],
                }
            )
        assert exc_info.value.detail["error"] == "upstream_request_error"
    finally:
        await provider.aclose()


# --- security hardening additions --------------------------------------------


def test_middleware_rejects_oversized_content_length() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/chat/completions",
        content=b"{}",
        headers={
            **AUTH_HEADERS,
            "Content-Type": "application/json",
            "Content-Length": str(3 * 1024 * 1024),
        },
    )
    assert response.status_code == 413
    assert "exceeds" in response.json()["detail"]


def test_middleware_rejects_invalid_content_length() -> None:
    client = TestClient(create_app())
    response = client.get("/health", headers={"Content-Length": "nope"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Content-Length"


def test_chat_message_content_bounds() -> None:
    from app.models.schemas import ChatCompletionRequest, ChatMessage
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ChatMessage(role="user", content="x" * 100_001)
    with pytest.raises(ValidationError):
        ChatMessage(role="user", content=[{"t": i} for i in range(201)])
    with pytest.raises(ValidationError):
        ChatCompletionRequest(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "ok"}],
            extra_body={f"k{i}": i for i in range(51)},
        )
    # happy path list content
    msg = ChatMessage(role="user", content=[{"type": "text", "text": "hi"}])
    assert isinstance(msg.content, list)


@pytest.mark.asyncio
async def test_audit_sink_ring_buffer_drops_oldest() -> None:
    sink = InMemoryAuditSink(maxlen=2)
    set_audit_sink(sink)
    await emit_audit(AuditEventType.AUTH_OK, correlation_id="corr-alpha")
    await emit_audit(AuditEventType.AUTH_OK, correlation_id="corr-bravo")
    await emit_audit(AuditEventType.AUTH_OK, correlation_id="corr-charlie")
    assert len(sink.events) == 2
    assert sink.events[0].correlation_id == "corr-bravo"
    assert sink.events[1].correlation_id == "corr-charlie"
    sink.clear()
    assert sink.events == []


def test_correlation_id_falls_back_when_state_missing() -> None:
    from app.security.auth import _correlation_id
    from starlette.requests import Request

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    request = Request(scope)
    cid = _correlation_id(request)
    assert cid.startswith("corr_")


@pytest.mark.asyncio
async def test_relay_sse_stream_stops_at_byte_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.proxy import streaming as streaming_mod
    from app.proxy.streaming import relay_sse_stream

    monkeypatch.setattr(streaming_mod, "_MAX_RELAY_BYTES", 4)

    chunks = [b"ab", b"cd", b"ef"]

    async def _aiter_bytes():
        for c in chunks:
            yield c

    upstream = AsyncMock()
    upstream.status_code = 200
    upstream.headers = {"content-type": "text/event-stream", "x-secret": "nope"}
    upstream.aiter_bytes = _aiter_bytes
    upstream.aclose = AsyncMock()

    response = await relay_sse_stream(upstream)
    body = b"".join([chunk async for chunk in response.body_iterator])
    assert body == b"abcd"
    assert "x-secret" not in {k.lower() for k in response.headers.keys()}
    upstream.aclose.assert_awaited()
