"""HTTPS + host allowlists for governance outbound HTTP."""

from __future__ import annotations

import os
from urllib.parse import urlparse


class EgressDeniedError(PermissionError):
    """Raised when an outbound URL fails the governance egress policy."""


_DEFAULT_LLM_HOSTS = frozenset(
    {
        "api.openai.com",
        "api.anthropic.com",
    }
)


def _split_hosts(raw: str | None) -> frozenset[str]:
    if not raw:
        return frozenset()
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def allowed_llm_hosts() -> frozenset[str]:
    extra = _split_hosts(os.getenv("GOVERNANCE_LLM_ALLOWED_HOSTS"))
    return _DEFAULT_LLM_HOSTS | extra


def assert_https_url(url: str, *, purpose: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise EgressDeniedError(
            f"{purpose} URL must use https:// (got {parsed.scheme or 'missing'}://"
            f"{parsed.netloc or url!r})"
        )
    if not parsed.hostname:
        raise EgressDeniedError(f"{purpose} URL is missing a hostname")
    if parsed.username or parsed.password:
        raise EgressDeniedError(f"{purpose} URL must not include userinfo")
    if parsed.port not in (None, 443):
        raise EgressDeniedError(f"{purpose} URL must use port 443 or default HTTPS")


def assert_allowed_llm_base_url(url: str) -> str:
    """Validate GOVERNANCE_LLM_BASE_URL (or equivalent) and return normalized base."""
    cleaned = url.rstrip("/")
    assert_https_url(cleaned, purpose="LLM")
    host = (urlparse(cleaned).hostname or "").lower()
    allowed = allowed_llm_hosts()
    if host not in allowed:
        raise EgressDeniedError(
            f"LLM host {host!r} is not allowlisted. "
            f"Allowed: {', '.join(sorted(allowed))}. "
            "Set GOVERNANCE_LLM_ALLOWED_HOSTS to add hosts."
        )
    return cleaned


def assert_allowed_dashboard_url(url: str) -> str:
    """Validate GOVERNANCE_DASHBOARD_URL — HTTPS required; optional host pin."""
    cleaned = url.rstrip("/")
    assert_https_url(cleaned, purpose="Dashboard")
    host = (urlparse(cleaned).hostname or "").lower()
    pinned = _split_hosts(os.getenv("GOVERNANCE_DASHBOARD_ALLOWED_HOSTS"))
    if pinned and host not in pinned:
        raise EgressDeniedError(
            f"Dashboard host {host!r} is not allowlisted "
            f"(GOVERNANCE_DASHBOARD_ALLOWED_HOSTS={', '.join(sorted(pinned))})"
        )
    return cleaned
