Title: Expand governance copyright signatures and Phase 1 quiz packs

## Summary

Grows governance §11.E.4-5 coverage without implementing the interceptor. Step 5 now has five additional FastAPI/httpx/provider/streaming/501 protected signatures, and Step 6 deterministic quiz generation teaches Phase 1 provider selection, streaming/SSE flow, and HTTP 501 checkpoint behavior.

## Design Decisions

- Keep signature expansion data-only in `known_snippets.json`.
- Add deterministic quiz content instead of relying on optional LLM enrichment.
- Keep Checkpoint #1 explicitly human-owned: agents must not fill `app/proxy/interceptor.py`.
- Use focused unit tests for generation and copyright matching.

## Changes

- Added five FastAPI/httpx anti-pattern signatures:
  - `fastapi_sync_httpx_in_async_route`
  - `httpx_async_client_per_stream_chunk`
  - `hardcoded_provider_bypass`
  - `checkpoint_501_catchall_mask`
  - `raw_sse_bytes_without_cleanup`
- Added Phase 1 glossary terms and quiz questions for providers, streaming/SSE, and HTTP 501.
- Added tests for new signature matching and deterministic quiz question generation.
- Added QRSPI artifacts under `thoughts/qrspi/2026-07-20-gov-copyright-quiz-packs/`.

## How to Verify

- `cd governance && python3 -m pytest tests/test_steps.py -k copyright`
- `cd governance && python3 -m pytest tests/test_steps.py -k comprehension`
- `cd governance && python3 -m pytest`
- `cd governance && python3 -m governance.cli run --root .. --skip-fuzz --skip-llm --no-fail-on-error`
- `git diff -- app/proxy/interceptor.py`

## Verification Performed

- Copyright focused tests: passed, 2 tests.
- Comprehension focused tests: passed, 2 tests.
- Full governance pytest: passed, 9 tests.
- Governance CLI smoke: passed; Comprehension Gate reported `PASS`.
- Interceptor diff: empty.

## References

- Ledger: `architecture_and_roadmap.md`
- QRSPI artifacts: `thoughts/qrspi/2026-07-20-gov-copyright-quiz-packs/`
- Design: `thoughts/qrspi/2026-07-20-gov-copyright-quiz-packs/design.md`
- Plan: `thoughts/qrspi/2026-07-20-gov-copyright-quiz-packs/plan.md`
- Mode: QRSPI Autonomous Mode, with product checkpoint ownership preserved.

## Interceptor Boundary

`app/proxy/interceptor.py` is untouched. Checkpoint #1 remains human-owned and blocked until the human completes it.
