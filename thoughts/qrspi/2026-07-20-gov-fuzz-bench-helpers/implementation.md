# Stage 7 Implementation Notes

## Completed

- Extracted the Anthropic payload mapper into `app/proxy/payloads.py` as `to_anthropic_payload`.
- Added `FUZZ_TARGETS = ("to_anthropic_payload",)` so Step 3 has an explicit real gateway pure helper target.
- Updated `AnthropicProvider` to call the extracted helper for streaming and non-streaming requests.
- Updated fuzz classification so `TypeError` and `ValueError` contract rejections are informational `rejected` results, while unexpected exceptions remain crashes.
- Added metrics for fuzz target names and rejection counts.
- Added benchmark per-PR injection API: `BenchmarkTarget`, `profile_target`, `profile_targets`, and `run(..., targets=...)`.
- Documented benchmark target injection in `governance/README.md`.
- Added focused tests in `governance/tests/test_fuzz_benchmark_helpers.py`.

## Verification

- `cd governance && python3 -m pytest tests/test_steps.py tests/test_fuzz_benchmark_helpers.py -q` -> 18 passed.
- `python3 -m pytest -q` -> 6 passed, 1 existing FastAPI/httpx deprecation warning.
- Task-scoped `cd governance && python3 -m governance.cli run --root .. --skip-llm --no-fail-on-error --json-out ../thoughts/qrspi/2026-07-20-gov-fuzz-bench-helpers/governance-report.json -f ...` -> passed with 0 blocking findings.
- Governance report fuzz metrics: `functions_tested == 1`, `crashes == 0`, target `app/proxy/payloads.py:to_anthropic_payload`.
- `git diff -- app/proxy/interceptor.py --exit-code` -> clean.

## Deviations

- The final focused tests live in a separate `governance/tests/test_fuzz_benchmark_helpers.py` file to avoid mixing this task with unrelated in-progress edits in `governance/tests/test_steps.py`.
