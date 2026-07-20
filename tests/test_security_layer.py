"""Layer D — security unit + contract tests."""

from __future__ import annotations

import pytest
from app.security.audit import (
    AUDIT_EVENTS_DDL,
    AuditEvent,
    AuditEventType,
    InMemoryAuditSink,
)
from app.security.egress import (
    ALLOWED_HOSTS,
    EgressDeniedError,
    assert_allowed_host,
    assert_allowed_url,
    is_allowed_url,
)


def test_egress_allows_openai_and_anthropic() -> None:
    assert is_allowed_url("https://api.openai.com/v1/chat/completions")
    assert is_allowed_url("https://api.anthropic.com/v1/messages")
    # Exact host membership (avoid substring checks CodeQL flags as weak URL sanitization)
    assert ALLOWED_HOSTS == frozenset({"api.openai.com", "api.anthropic.com"})
    assert_allowed_host("api.openai.com")
    assert_allowed_host("API.Anthropic.Com")


def test_egress_denies_http_and_unknown_hosts() -> None:
    assert not is_allowed_url("http://api.openai.com/v1/chat/completions")
    assert not is_allowed_url("https://evil.example.com/v1")
    assert not is_allowed_url(None)
    assert not is_allowed_url(-1)
    assert not is_allowed_url({"__proto__": "x"})
    with pytest.raises(EgressDeniedError):
        assert_allowed_url("https://evil.example.com/exfil")
    with pytest.raises(EgressDeniedError):
        assert_allowed_host("evil.example.com")
    with pytest.raises(TypeError):
        assert_allowed_url(-1)
    with pytest.raises(TypeError):
        assert_allowed_host(None)


@pytest.mark.asyncio
async def test_audit_sink_records_events() -> None:
    sink = InMemoryAuditSink()
    event = AuditEvent(
        event_type=AuditEventType.EGRESS_DENIED,
        correlation_id="corr-1",
        blocked=True,
        reason="host not allowlisted",
    )
    stored = await sink.write(event)
    assert stored.id == event.id
    assert len(sink.events) == 1
    assert "CREATE TABLE" in AUDIT_EVENTS_DDL


@pytest.mark.asyncio
async def test_egress_checked_client_denies_unknown_host() -> None:
    from app.security.http import EgressCheckedAsyncClient

    client = EgressCheckedAsyncClient(timeout=1.0)
    try:
        with pytest.raises(EgressDeniedError):
            await client.request("GET", "https://evil.example.com/exfil")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_egress_checked_client_allows_openai_via_mock_transport() -> None:
    import httpx
    from app.security.http import EgressCheckedAsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.openai.com"
        return httpx.Response(200, json={"ok": True})

    client = EgressCheckedAsyncClient(transport=httpx.MockTransport(handler), timeout=1.0)
    try:
        resp = await client.request("POST", "https://api.openai.com/v1/chat/completions")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
    finally:
        await client.aclose()
