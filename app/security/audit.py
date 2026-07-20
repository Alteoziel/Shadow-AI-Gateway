"""Layer E — audit log schema scaffold (Phase 3 target: Supabase Postgres).

No live DB required yet. Models define the enterprise audit trail contract so
Phase 3 inserts map cleanly to compliance fields.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEventType(StrEnum):
    REQUEST_RECEIVED = "request_received"
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


class InMemoryAuditSink:
    """Dev/test sink until Supabase is wired in Phase 3."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def write(self, event: AuditEvent) -> AuditEvent:
        self.events.append(event)
        return event
