"""Shared pytest fixtures for gateway tests."""

from __future__ import annotations

import os

import pytest

# Must be set before app.config Settings is first loaded in workers.
os.environ.setdefault("GATEWAY_API_KEY", "test-gateway-key")
os.environ.setdefault("GATEWAY_RATE_LIMIT_PER_MINUTE", "1000")

TEST_GATEWAY_API_KEY = os.environ["GATEWAY_API_KEY"]
AUTH_HEADERS = {"Authorization": f"Bearer {TEST_GATEWAY_API_KEY}"}


@pytest.fixture(autouse=True)
def _reset_security_state() -> None:
    from app.config import clear_settings_cache
    from app.security.audit import get_audit_sink
    from app.security.rate_limit import reset_rate_limit_state

    clear_settings_cache()
    reset_rate_limit_state()
    get_audit_sink().clear()
    yield
    reset_rate_limit_state()
    get_audit_sink().clear()
    clear_settings_cache()
