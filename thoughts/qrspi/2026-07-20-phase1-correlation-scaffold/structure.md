# Structure Outline

## Approach

Add correlation and request logging scaffolding around the existing FastAPI request lifecycle, keeping the human-owned interceptor body unimplemented. Validate the behavior through focused pytest coverage for helpers, response headers, request logs, and the unchanged checkpoint contract.

## Phase 1: Correlation Middleware and Contract Tests

This phase delivers end-to-end observability scaffolding for `/health` and `/v1/chat/completions`: inbound/generate correlation ID, request state metadata, lifecycle logs, response header propagation, and chat call-site context.

**Files**: `app/proxy/correlation.py`, `app/main.py`, `app/api/v1/chat.py`, `app/proxy/interceptor.py`, `tests/test_correlation.py`, `tests/test_health.py`, `tests/test_proxy_routing.py`, `tests/test_interceptor_contract.py`

**Key changes**:

- `CORRELATION_ID_HEADER: str` — shared header name.
- `generate_correlation_id() -> str` — create a prefixed UUID correlation ID.
- `parse_correlation_id(headers: Mapping[str, str] | Headers) -> str` — return a valid inbound ID or generate a new one.
- `received_at_iso() -> str` — timestamp helper for request metadata.
- `@app.middleware("http")` — store `request.state.correlation_id` / `request.state.received_at`, log lifecycle, and set `X-Correlation-ID`.
- `chat_completions(...)` — include correlation context in metadata and logs without changing interceptor behavior.

**Verify**: `pytest tests/test_correlation.py tests/test_health.py tests/test_proxy_routing.py tests/test_interceptor_contract.py` passes; `POST /v1/chat/completions` still returns 501 when the interceptor is not monkeypatched.

---

## Phase 2: Full Gateway Verification and PR Draft

This phase runs the project test suite, updates plan checkboxes, writes the draft PR body, and pushes the requested branch.

**Files**: `thoughts/qrspi/2026-07-20-phase1-correlation-scaffold/plan.md`, `/workspace/.pr-drafts/agent4.md`

**Key changes**:

- `plan.md` verification checkboxes reflect executed commands.
- `agent4.md` summarizes Ledger constraints, QRSPI artifacts, changes, and verification.

**Verify**: `pytest` passes; `git diff` confirms `app/proxy/interceptor.py` still raises `NotImplementedError`; `git push -u origin cursor/phase1-correlation-scaffold-5e0d` succeeds.

## Testing Checkpoints

- After Phase 1, helper unit tests and route tests show correlation IDs are generated/propagated and the 501 path still works.
- After Phase 2, the full gateway test suite passes and the PR draft is ready for the remote PR automation.
