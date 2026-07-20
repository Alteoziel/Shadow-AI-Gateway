# Implementation Plan

## Overview

Add correlation ID helpers and FastAPI request logging around the existing Phase 1 gateway without implementing Human Checkpoint #1. The final state must cover `/health` and the current 501 chat path while preserving `intercept_outbound_request` as `NotImplementedError`.

## Autonomous Assumptions

- Standard library logging is the right observability mechanism for this scaffold because the gateway already uses it and no structured logging dependency exists.
- `X-Correlation-ID` is the only accepted inbound header for now; generated IDs are used for missing or invalid values.
- Manual verification is converted to pytest and source inspection because this is a non-UI gateway change.

## Phase 1: Correlation Middleware and Contract Tests

### Changes

#### 1. Correlation helper module

**File**: `app/proxy/correlation.py`  
**Action**: create

- Define `CORRELATION_ID_HEADER = "X-Correlation-ID"`.
- Define `generate_correlation_id() -> str` returning `corr_` plus UUID hex.
- Define `parse_correlation_id(headers: Mapping[str, str]) -> str`; trim inbound header, accept printable values of conservative length, otherwise generate.
- Define `received_at_iso() -> str` returning timezone-aware UTC ISO text.

#### 2. FastAPI middleware

**File**: `app/main.py`  
**Action**: modify

- Import `time`, `Request`, `Response`, and helper functions.
- Add module logger.
- Add `@app.middleware("http")` inside `create_app()` before router inclusion.
- For every request, resolve correlation ID, set `request.state.correlation_id` and `request.state.received_at`, call downstream handler, set response `X-Correlation-ID`, and log method/path/status/elapsed/correlation/received_at.
- On exceptions, log the same context with `logger.exception` and re-raise.

#### 3. Chat call-site context

**File**: `app/api/v1/chat.py`  
**Action**: modify

- Read `correlation_id` and `received_at` from `request.state`.
- Include those values in metadata passed to `intercept_outbound_request`; do not add them to `body`.
- Add a pre-interceptor info log and include correlation ID in the existing checkpoint warning.

#### 4. Checkpoint comment only

**File**: `app/proxy/interceptor.py`  
**Action**: modify comments only

- Update the cheat sheet comment to point the human toward `app/proxy/correlation.py` and request metadata.
- Keep the `raise NotImplementedError(...)` body unchanged in behavior.

#### 5. Tests

**Files**: `tests/test_correlation.py`, `tests/test_health.py`, `tests/test_proxy_routing.py`, `tests/test_interceptor_contract.py`  
**Action**: create/modify

- Add helper tests for generated, accepted, invalid, and timestamp values.
- Assert `/health` returns `X-Correlation-ID`, preserves a valid inbound ID, and emits a lifecycle log.
- Assert `/v1/chat/completions` 501 responses include `X-Correlation-ID`.
- Assert monkeypatched interceptor receives metadata with path/correlation context while still not testing checkpoint implementation.
- Add source-level assertion that `intercept_outbound_request` still raises `NotImplementedError`.

### Verification

#### Automated

- [x] `python3 -m pytest tests/test_correlation.py tests/test_health.py tests/test_proxy_routing.py tests/test_interceptor_contract.py` passes.
- [x] `python3 -m pytest tests/test_interceptor_contract.py::test_intercept_outbound_request_raises_not_implemented` passes.

#### Manual

- [x] autonomous: verified via pytest that `/health` emits a correlation header and request log.
- [x] autonomous: verified via pytest that unpatched chat still returns 501 and includes a correlation header.

---

## Phase 2: Full Gateway Verification and PR Draft

### Changes

#### 1. Update plan progress

**File**: `thoughts/qrspi/2026-07-20-phase1-correlation-scaffold/plan.md`  
**Action**: modify

- Check completed verification items after commands pass.

#### 2. PR draft

**File**: `.pr-drafts/agent4.md`  
**Action**: create

- Include summary, design decisions, changes, verification, Ledger reference, and QRSPI artifact directory.

#### 3. Git operations

**Action**: commit and push

- Commit Phase 1 implementation after targeted verification passes.
- Commit PR draft / final artifact updates after full verification passes.
- Push with `git push -u origin cursor/phase1-correlation-scaffold-5e0d`.

### Verification

#### Automated

- [x] `python3 -m pytest` passes.
- [x] `python3 - <<'PY' ...` source inspection confirms `intercept_outbound_request` still contains `NotImplementedError`.
- [ ] `git push -u origin cursor/phase1-correlation-scaffold-5e0d` succeeds.

#### Manual

- [x] autonomous: verified via `git diff origin/cursor/qrspi-ledger-land-5e0d...HEAD -- app/proxy/interceptor.py` that only comments changed in the interceptor file.
