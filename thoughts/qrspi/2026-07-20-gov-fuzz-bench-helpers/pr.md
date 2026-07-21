# Stage 8 PR Notes

## Summary

Step 3 now targets a real gateway pure helper by extracting the Anthropic payload mapper and registering it for fuzzing. Step 4 now has an informational benchmark injection API and README documentation for per-PR use.

## Design Decisions

- Use explicit `FUZZ_TARGETS` registration rather than broad private/class-method discovery.
- Treat `TypeError` and `ValueError` as helper contract rejections, not crashes.
- Keep benchmark injection caller-driven and informational.
- Leave `app/proxy/interceptor.py` untouched and still blocked on human implementation.

## Verification

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
