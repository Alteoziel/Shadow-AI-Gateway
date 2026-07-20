from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal


ScrubAction = Literal["redact", "flag"]


@dataclass(frozen=True)
class ScrubFinding:
    """Future finding metadata emitted by the human-owned scrub loop."""

    kind: str
    start: int
    end: int
    replacement: str
    action: ScrubAction = "redact"
    confidence: float | None = None


@dataclass(frozen=True)
class ScrubRequest:
    """Input contract for the Phase 2 scrub pipeline."""

    text: str
    metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ScrubResult:
    """Output contract for sanitized prompt text and scrub metadata."""

    original_text: str
    sanitized_text: str
    findings: tuple[ScrubFinding, ...]
    elapsed_ms: float
