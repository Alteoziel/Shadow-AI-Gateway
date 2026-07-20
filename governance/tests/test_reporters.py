"""Tests for GitHub / dashboard reporters."""

from __future__ import annotations

from governance.models import PipelineReport, StepResult
from governance.reporters.github import QUIZ_STATUS_CONTEXT, post_quiz_commit_status


def test_quiz_status_skipped_without_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    report = PipelineReport(
        passed=True,
        steps=[StepResult(step="x", name="X", passed=True)],
        repo="Alteoziel/Shadow-AI-Gateway",
        commit_sha="abc1234",
    )
    assert post_quiz_commit_status(report) is None


def test_quiz_status_posts_pending(monkeypatch) -> None:
    calls: list[dict] = []

    class _Resp:
        status_code = 201

        def json(self) -> dict:
            return {"id": 1, "state": "pending", "context": QUIZ_STATUS_CONTEXT}

    class _Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def post(self, url, headers=None, json=None):
            calls.append({"url": url, "headers": headers, "json": json})
            return _Resp()

    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr("governance.reporters.github.httpx.Client", _Client)

    report = PipelineReport(
        passed=True,
        steps=[StepResult(step="x", name="X", passed=True)],
        repo="Alteoziel/Shadow-AI-Gateway",
        commit_sha="deadbeefcafebabe",
    )
    result = post_quiz_commit_status(report, state="pending")
    assert result is not None
    assert result.get("state") == "pending"
    assert len(calls) == 1
    assert calls[0]["url"].endswith("/statuses/deadbeefcafebabe")
    assert calls[0]["json"]["context"] == QUIZ_STATUS_CONTEXT
    assert calls[0]["json"]["state"] == "pending"
