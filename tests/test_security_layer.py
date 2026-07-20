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
    assert "api.openai.com" in ALLOWED_HOSTS
    assert "api.anthropic.com" in ALLOWED_HOSTS
    assert_allowed_host("api.openai.com")
    assert_allowed_host("API.Anthropic.Com")


def test_egress_denies_http_and_unknown_hosts() -> None:
    assert not is_allowed_url("http://api.openai.com/v1/chat/completions")
    assert not is_allowed_url("https://evil.example.com/v1")
    with pytest.raises(EgressDeniedError):
        assert_allowed_url("https://evil.example.com/exfil")
    with pytest.raises(EgressDeniedError):
        assert_allowed_host("evil.example.com")


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
