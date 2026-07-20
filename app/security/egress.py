"""Layer E — egress allowlist for upstream LLM providers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class EgressTarget:
    name: str
    host: str
    scheme: str = "https"


ALLOWED_EGRESS: tuple[EgressTarget, ...] = (
    EgressTarget(name="openai", host="api.openai.com"),
    EgressTarget(name="anthropic", host="api.anthropic.com"),
)

ALLOWED_HOSTS: frozenset[str] = frozenset(t.host.lower() for t in ALLOWED_EGRESS)


class EgressDeniedError(PermissionError):
    """Raised when an outbound URL is not on the allowlist."""


def is_allowed_url(url: str) -> bool:
    """Return True if URL host is on the egress allowlist and uses https."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    return host in ALLOWED_HOSTS


def assert_allowed_url(url: str) -> None:
    if not is_allowed_url(url):
        raise EgressDeniedError(
            f"Egress denied for URL host (not on allowlist): {url!r}. "
            f"Allowed hosts: {sorted(ALLOWED_HOSTS)}"
        )


def assert_allowed_host(host: str) -> None:
    normalized = host.lower().strip()
    if normalized not in ALLOWED_HOSTS:
        raise EgressDeniedError(
            f"Egress denied for host {host!r}. Allowed: {sorted(ALLOWED_HOSTS)}"
        )
