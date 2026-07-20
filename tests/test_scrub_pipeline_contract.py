import inspect
from pathlib import Path

import pytest
from app.scrub import SCRUB_LATENCY_BUDGET_MS, ScrubRequest, scrub_prompt


def test_scrub_prompt_exists_and_is_async():
    assert callable(scrub_prompt)
    assert inspect.iscoroutinefunction(scrub_prompt)


@pytest.mark.asyncio
async def test_scrub_pipeline_stub_raises_not_implemented():
    request = ScrubRequest(text="Contact Alice at alice@example.com")

    with pytest.raises(NotImplementedError) as exc_info:
        await scrub_prompt(request)

    message = str(exc_info.value)
    assert "Checkpoint #2" in message
    assert "app/scrub/pipeline.py" in message


def test_scrub_latency_budget_is_documented():
    pipeline_path = (
        Path(__file__).resolve().parents[1] / "app" / "scrub" / "pipeline.py"
    )
    source = pipeline_path.read_text(encoding="utf-8")

    assert SCRUB_LATENCY_BUDGET_MS == 100
    assert "TODO: Human Hands-On Implementation" in source
    assert "sub-100ms" in source
    assert "NotImplementedError" in source


def test_scrub_not_wired_into_phase1_route_or_interceptor():
    repo_root = Path(__file__).resolve().parents[1]
    phase1_paths = [
        repo_root / "app" / "api" / "v1" / "chat.py",
        repo_root / "app" / "proxy" / "interceptor.py",
    ]
    forbidden_tokens = (
        "app.scrub",
        "scrub_prompt",
        "SCRUB_LATENCY_BUDGET_MS",
    )

    for path in phase1_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in source
