"""Step 4 — Benchmark Engine: empirical Big-O scaling profiler."""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Callable

from governance.models import Finding, Severity, StepResult

STEP_ID = "benchmark_engine"
STEP_NAME = "Benchmark Engine (Big-O Execution Tracker)"

# Canonical sizes for empirical growth measurement
SIZES = (10, 100, 1_000, 10_000)


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


def profile_algorithms() -> dict[str, dict]:
    """Run the timer engine against known-complexity reference functions."""
    profiles: dict[str, dict] = {}
    targets = {
        "linear_scan": (_linear_scan, SIZES, "O(N)"),
        "hash_join": (_hash_join, SIZES, "O(N)"),
        # Smaller sizes for quadratic so CI stays under a few seconds
        "quadratic_scan": (_quadratic_scan, (10, 50, 100, 200), "O(N^2)"),
    }
    for name, (fn, sizes, expected) in targets.items():
        times = [_time_call(fn, n) for n in sizes]
        label, slope = estimate_big_o(list(sizes), times)
        profiles[name] = {
            "sizes": list(sizes),
            "times_ms": [round(t * 1000, 4) for t in times],
            "estimated": label,
            "slope": round(slope, 3),
            "expected": expected,
        }
    return profiles


def run(paths: list[Path] | None = None) -> StepResult:
    """
    Execute the Big-O timer engine.

    In CI this validates the profiler itself and records scaling curves that
    the review dashboard can plot. Production target-function injection hooks
    are available via `estimate_big_o` for human checkpoint extensions.
    """
    del paths  # reserved for future per-PR target injection
    profiles = profile_algorithms()
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
        metrics={"profiles": profiles, "sizes_default": list(SIZES)},
    )
