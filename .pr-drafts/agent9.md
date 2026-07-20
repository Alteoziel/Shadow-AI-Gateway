# Phase 2 scrub checkpoint scaffold

## Summary

Prepares Phase 2 Walk scaffolding for the human-owned scrub pipeline without implementing scrub logic or wiring it into request flow.

## Design Decisions

- Add `app/scrub/pipeline.py` as the Phase 2 checkpoint path with `TODO: Human Hands-On Implementation`, a 3-bullet cheat sheet, and `NotImplementedError`.
- Keep Phase 2 status and checkpoint status as `not_started`; this branch only prepares the path.
- Keep Checkpoint #1 at `app/proxy/interceptor.py` as `blocked_on_human`.
- Add lightweight dataclass contracts and a latency-budget constant instead of regex/NLP behavior.

## Changes

- Created `app/scrub/` with public contracts, `SCRUB_LATENCY_BUDGET_MS = 100`, and async `scrub_prompt(...)` stub.
- Added `tests/test_scrub_pipeline_contract.py` to assert the stub raises, documents sub-100ms, and remains unwired from Phase 1 files.
- Updated `architecture_and_roadmap.md` Phase 2 checkpoint path references to `app/scrub/pipeline.py`.
- Added QRSPI artifacts under `thoughts/qrspi/2026-07-20-phase2-scrub-stub/`.

## How to Verify

- `python3 -m pytest tests/test_scrub_pipeline_contract.py tests/test_interceptor_contract.py tests/test_proxy_routing.py`
- `python3 -m pytest`
- `rg "app\\.scrub|scrub_prompt|SCRUB_LATENCY_BUDGET_MS" app/api/v1/chat.py app/proxy/interceptor.py` should return no matches.

## References

- Ledger: `architecture_and_roadmap.md`
- QRSPI artifacts: `thoughts/qrspi/2026-07-20-phase2-scrub-stub/`
- Design: `thoughts/qrspi/2026-07-20-phase2-scrub-stub/design.md`
- Plan: `thoughts/qrspi/2026-07-20-phase2-scrub-stub/plan.md`

## Scope Confirmation

- No real scrub loop was implemented.
- `app/proxy/interceptor.py` was not implemented or modified.
- Scrub code is not wired into `app/api/v1/chat.py` or `app/proxy/interceptor.py`.
- QRSPI was run under Autonomous Mode.
