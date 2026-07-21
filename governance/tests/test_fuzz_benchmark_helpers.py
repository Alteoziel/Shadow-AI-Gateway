from __future__ import annotations

from pathlib import Path

from governance.steps import benchmark_engine, fuzz_chamber
from governance.steps.benchmark_engine import BenchmarkTarget

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_fuzz_chamber_targets_real_gateway_helper() -> None:
    result = fuzz_chamber.run([REPO_ROOT / "app" / "proxy" / "payloads.py"])

    assert result.passed
    assert result.metrics["functions_tested"] >= 1
    assert result.metrics["crashes"] == 0
    assert any("to_anthropic_payload" in t for t in result.metrics["targets"])


def test_fuzz_chamber_skips_human_checkpoint_interceptor() -> None:
    result = fuzz_chamber.run([REPO_ROOT / "app" / "proxy" / "interceptor.py"])

    assert result.passed
    assert result.metrics["functions_tested"] == 0
    assert result.metrics["targets"] == []


def test_benchmark_engine_profiles_injected_targets() -> None:
    def linear_target(data: list[int]) -> int:
        return sum(data)

    result = benchmark_engine.run(
        targets=[
            BenchmarkTarget(
                name="pr_linear_target",
                fn=linear_target,
                sizes=(10, 100, 1_000),
                expected="O(N)",
            )
        ]
    )

    assert result.passed
    assert "pr_linear_target" in result.metrics["injected_profiles"]
    assert result.metrics["injected_profiles"]["pr_linear_target"]["expected"] == "O(N)"
