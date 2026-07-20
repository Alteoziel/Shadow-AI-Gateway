"""Shared result models for the six-step governance pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Finding(BaseModel):
    step: str
    severity: Severity
    message: str
    file: str | None = None
    line: int | None = None
    rule_id: str | None = None
    evidence: str | None = None
    suggestion: str | None = None


class StepResult(BaseModel):
    step: str
    name: str
    passed: bool
    findings: list[Finding] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    skipped: bool = False
    skip_reason: str | None = None


class PipelineReport(BaseModel):
    passed: bool
    steps: list[StepResult]
    summary: dict[str, Any] = Field(default_factory=dict)
    pr_number: int | None = None
    commit_sha: str | None = None
    repo: str | None = None

    def error_count(self) -> int:
        return sum(
            1
            for step in self.steps
            for f in step.findings
            if f.severity in (Severity.ERROR, Severity.CRITICAL)
        )
