# Task

Add a gateway-focused test matrix and an independent GitHub Actions workflow that validates the Phase 1 FastAPI proxy contract around Human Checkpoint #1 without implementing the checkpoint. The work must prove provider selection, upstream payload construction, Anthropic payload mapping, streaming relay behavior, and the documented post-checkpoint unlock path while preserving the current 501 response and `NotImplementedError` in `app/proxy/interceptor.py`.

## Scope Constraints

- Base branch: `origin/cursor/qrspi-ledger-land-5e0d`.
- Feature branch: `cursor/phase1-gateway-ci-5e0d`.
- Artifacts: `thoughts/qrspi/2026-07-20-phase1-gateway-ci/`.
- Do not weaken `tests/test_interceptor_contract.py`.
- Do not implement `app/proxy/interceptor.py`.
- Add development dependencies only as needed for mocked gateway tests.

## Rejected Alternate Framings

- Testing the checkpoint implementation itself was rejected because The Ledger marks Checkpoint #1 as human-owned.
- Folding gateway tests into governance CI was rejected because the task asks for an app-focused workflow independent of governance.
