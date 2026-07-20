"""Step 4 — Benchmark Engine: empirical Big-O scaling profiler."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import math
import time
from pathlib import Path
from typing import Callable

from governance.models import Finding, Severity, StepResult

STEP_ID = "benchmark_engine"
STEP_NAME = "Benchmark Engine (Big-O Execution Tracker)"

# Canonical sizes for empirical growth measurement
SIZES = (10, 100, 1_000, 10_000)


@dataclass(frozen=True)
class BenchmarkTarget:
    """A per-PR benchmark target supplied by custom checks or tests."""

    name: str
    fn: Callable[[list[int]], object]
    sizes: Sequence[int] = SIZES
    expected: str | None = None
    repeats: int = 3


def _time_call(fn: Callable[[list[int]], object], n: int, repeats: int = 3) -> float:
    data = list(range(n))
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        fn(data)
        best = min(best, time.perf_counter() - start)
    return best


def estimate_big_o(sizes: list[int], times: list[float]) -> tuple[str, float]:
    """
    Derive a rough Big-O label from size/time pairs using log-log slope.

    slope ≈ 0 → O(1)
    slope ≈ 1 → O(N)
    slope ≈ 2 → O(N²)
    """
    # Use largest two stable points (avoid tiny-N noise)
    pairs = [(s, t) for s, t in zip(sizes, times) if t > 0 and s > 0]
    if len(pairs) < 2:
        return "unknown", 0.0

    (n1, t1), (n2, t2) = pairs[-2], pairs[-1]
    slope = math.log(t2 / t1) / math.log(n2 / n1)

    if slope < 0.3:
        label = "O(1)"
    elif slope < 1.3:
        label = "O(N)"
    elif slope < 1.8:
        label = "O(N log N)"
    elif slope < 2.5:
        label = "O(N^2)"
    else:
        label = "O(N^3+)"
    return label, slope


# Reference algorithms used as the engine's self-check + demo profile
def _linear_scan(data: list[int]) -> int:
    total = 0
    for x in data:
        total += x
    return total


def _quadratic_scan(data: list[int]) -> int:
    # Intentionally O(N^2) — used only as a calibration target, not production code
    total = 0
    n = min(len(data), 800)  # cap to keep CI fast
    for i in range(n):
        for j in range(n):
            total += data[i] + data[j]
    return total


def _hash_join(data: list[int]) -> int:
    seen = set(data)
    return sum(1 for x in data if (x * 2) in seen)


def profile_target(target: BenchmarkTarget) -> dict[str, object]:
    """Profile a caller-supplied target function over its configured sizes."""
    times = [_time_call(target.fn, n, repeats=target.repeats) for n in target.sizes]
    label, slope = estimate_big_o(list(target.sizes), times)
    profile: dict[str, object] = {
        "sizes": list(target.sizes),
        "times_ms": [round(t * 1000, 4) for t in times],
        "estimated": label,
        "slope": round(slope, 3),
    }
    if target.expected is not None:
        profile["expected"] = target.expected
    return profile


def profile_targets(targets: Iterable[BenchmarkTarget]) -> dict[str, dict[str, object]]:
    """Profile all caller-supplied targets by name."""
    return {target.name: profile_target(target) for target in targets}


def profile_algorithms() -> dict[str, dict]:
    """Run the timer engine against known-complexity reference functions."""
    targets = {
        "linear_scan": BenchmarkTarget("linear_scan", _linear_scan, SIZES, "O(N)"),
        "hash_join": BenchmarkTarget("hash_join", _hash_join, SIZES, "O(N)"),
        # Smaller sizes for quadratic so CI stays under a few seconds
        "quadratic_scan": BenchmarkTarget(
            "quadratic_scan", _quadratic_scan, (10, 50, 100, 200), "O(N^2)"
        ),
    }
    return profile_targets(targets.values())


def run(
    paths: list[Path] | None = None,
    targets: Iterable[BenchmarkTarget] | None = None,
) -> StepResult:
    """
    Execute the Big-O timer engine.

    In CI this validates the profiler itself and records scaling curves that
    the review dashboard can plot. Production target-function injection hooks
    are available via `estimate_big_o` for human checkpoint extensions.
    """
    del paths  # reserved for future automatic target discovery
    profiles = profile_algorithms()
    injected_profiles = profile_targets(targets) if targets is not None else {}
    findings: list[Finding] = []

    # Flag if the linear reference is misclassified as quadratic+ (engine bug)
    linear = profiles["linear_scan"]
    if linear["estimated"] in {"O(N^2)", "O(N^3+)"}:
        findings.append(
            Finding(
                step=STEP_ID,
                severity=Severity.WARNING,
                message=(
                    f"linear_scan estimated as {linear['estimated']} "
                    f"(slope={linear['slope']}) — noisy environment?"
                ),
                rule_id="BENCH001_NOISE",
            )
        )

    # Educational assertion: quadratic should not look like O(1)/O(N) on large slope
    quadratic = profiles["quadratic_scan"]
    if quadratic["slope"] < 1.4:
        findings.append(
            Finding(
                step=STEP_ID,
                severity=Severity.INFO,
                message=(
                    f"quadratic_scan slope={quadratic['slope']} lower than expected; "
                    "JIT/noise may compress the curve on small N."
                ),
                rule_id="BENCH002_CALIBRATION",
            )
        )

    return StepResult(
        step=STEP_ID,
        name=STEP_NAME,
        passed=True,  # informational profiler — does not block unless extended
        findings=findings,
        metrics={
            "profiles": profiles,
            "injected_profiles": injected_profiles,
            "sizes_default": list(SIZES),
        },
    )
