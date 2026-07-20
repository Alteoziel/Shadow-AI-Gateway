# Target real helpers in fuzz and benchmark hooks

## Summary

- Extracts the Anthropic payload mapper into `app/proxy/payloads.py` as a real gateway pure helper and registers it for fuzzing.
- Updates Step 3 fuzzing to record expected `TypeError` / `ValueError` contract rejections without treating them as crashes.
- Adds Step 4 benchmark target injection API plus README docs for per-PR informational profiling.

## Design Decisions

- Explicit `FUZZ_TARGETS` registration keeps fuzz aimed at known pure helpers instead of accidentally touching route handlers or human checkpoints.
- The interceptor is still excluded and untouched; `app/proxy/interceptor.py` remains the human-owned Checkpoint #1.
- Benchmark injection is caller-driven and informational, preserving the current non-blocking Step 4 behavior.

## Changes

- `app/proxy/payloads.py`: new `to_anthropic_payload(...)` helper.
- `app/proxy/providers/anthropic.py`: uses the extracted helper for stream and non-stream paths.
- `governance/governance/steps/fuzz_chamber.py`: explicit target discovery, rejection classification, target/rejection metrics, checkpoint skip.
- `governance/governance/steps/benchmark_engine.py`: `BenchmarkTarget`, `profile_target`, `profile_targets`, and injected metrics.
- `governance/tests/test_fuzz_benchmark_helpers.py`: focused fuzz and benchmark coverage.
- `governance/README.md`: per-PR benchmark injection docs.

## How to Verify

- `cd governance && python3 -m pytest tests/test_steps.py tests/test_fuzz_benchmark_helpers.py -q`
- `python3 -m pytest -q`
- `cd governance && python3 -m governance.cli run --root .. --skip-llm --no-fail-on-error --json-out ../thoughts/qrspi/2026-07-20-gov-fuzz-bench-helpers/governance-report.json`
- `git diff -- app/proxy/interceptor.py --exit-code`

## References

- Ledger: `architecture_and_roadmap.md`
- QRSPI artifacts: `thoughts/qrspi/2026-07-20-gov-fuzz-bench-helpers/`
- Design: `thoughts/qrspi/2026-07-20-gov-fuzz-bench-helpers/design.md`
- Plan: `thoughts/qrspi/2026-07-20-gov-fuzz-bench-helpers/plan.md`

QRSPI ran under Autonomous Mode.
