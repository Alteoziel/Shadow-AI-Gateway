"""Layer E — audit log schema + process-wide sink (Phase 3 → Postgres).

In-memory sink is wired on the request path now so future code always has an
audit hook. Phase 3 swaps the sink implementation for Supabase without
changing call sites.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEventType(StrEnum):
    REQUEST_RECEIVED = "request_received"
    AUTH_OK = "auth_ok"
    AUTH_DENIED = "auth_denied"
    RATE_LIMITED = "rate_limited"
    INTERCEPTOR_OK = "interceptor_ok"
    INTERCEPTOR_BLOCK = "interceptor_block"
    PII_REDACTED = "pii_redacted"
    PROVIDER_CALL = "provider_call"
    PROVIDER_ERROR = "provider_error"
    EGRESS_DENIED = "egress_denied"


class AuditEvent(BaseModel):
    """Immutable-ish audit record for a single gateway decision/action."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: AuditEventType
    correlation_id: str
    user_id: str | None = None
    provider: str | None = None
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    blocked: bool = False
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# Suggested Postgres DDL (Phase 3) — keep in sync with AuditEvent fields.
AUDIT_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    user_id TEXT,
    provider TEXT,
    model TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    blocked BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_audit_events_ts ON audit_events (ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_correlation ON audit_events (correlation_id);
"""


class AuditSink(Protocol):
    async def write(self, event: AuditEvent) -> AuditEvent: ...


class InMemoryAuditSink:
    """Dev/test / Phase-1 sink until Supabase is wired in Phase 3."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def write(self, event: AuditEvent) -> AuditEvent:
        self.events.append(event)
        return event

    def clear(self) -> None:
        self.events.clear()


_sink: InMemoryAuditSink = InMemoryAuditSink()


def get_audit_sink() -> InMemoryAuditSink:
    return _sink


def set_audit_sink(sink: InMemoryAuditSink) -> None:
    """Replace process sink (tests)."""
    global _sink
    _sink = sink


async def emit_audit(
    event_type: AuditEventType,
    *,
    correlation_id: str,
    blocked: bool = False,
    reason: str | None = None,
    user_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        correlation_id=correlation_id or "unknown",
        blocked=blocked,
        reason=reason,
        user_id=user_id,
        provider=provider,
        model=model,
        metadata=metadata or {},
    )
    return await get_audit_sink().write(event)
