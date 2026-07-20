# Draft PR: Phase 1 correlation scaffold

## Summary

Adds observability scaffolding outside Human Checkpoint #1 for the Phase 1 gateway. Requests now receive a correlation ID, responses propagate `X-Correlation-ID`, and middleware logs request lifecycle events for both `/health` and the current 501 chat path.

## Design Decisions

- Keep correlation helpers in `app/proxy/correlation.py` to stay close to the proxy request path without adding a new observability package.
- Accept a single inbound `X-Correlation-ID` header and generate `corr_<uuid>` IDs when the inbound value is missing or invalid.
- Store request lifecycle context on `request.state` and response headers only; do not attach `correlation_id` or `received_at` inside `intercept_outbound_request`.
- Update `app/proxy/interceptor.py` comments only to point the future human implementation at the helper.

## Changes

- Added `app/proxy/correlation.py` for ID generation, inbound parsing, and received-at timestamps.
- Added FastAPI middleware in `app/main.py` for request state, lifecycle logs, and response header propagation.
- Added chat route log context around the interceptor call while preserving the existing 501 checkpoint path.
- Added tests for helper behavior, health request logging/header propagation, chat 501 correlation headers, and the unchanged interceptor contract.

## How to Verify

- `python3 -m pytest tests/test_correlation.py tests/test_health.py tests/test_proxy_routing.py tests/test_interceptor_contract.py`
- `python3 -m pytest tests/test_interceptor_contract.py::test_intercept_outbound_request_raises_not_implemented`
- `python3 -m pytest`
- `python3 - <<'PY' ...` source inspection confirmed `intercept_outbound_request` still contains `raise NotImplementedError`.
- `git diff origin/cursor/qrspi-ledger-land-5e0d...HEAD -- app/proxy/interceptor.py` shows only a comment update.

## References

- The Ledger: `architecture_and_roadmap.md`
- QRSPI artifacts: `thoughts/qrspi/2026-07-20-phase1-correlation-scaffold/`
- Design: `thoughts/qrspi/2026-07-20-phase1-correlation-scaffold/design.md`
- Plan: `thoughts/qrspi/2026-07-20-phase1-correlation-scaffold/plan.md`
- QRSPI mode: Autonomous Mode, with Human Checkpoint #1 left blocked on human implementation.
