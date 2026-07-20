# Implementation Plan

## Overview

Add Gateway-specific AST governance rules for Ledger §11.E.1: block synchronous `httpx` / `requests` usage in `app/`, structurally verify chat-route interceptor ordering, and prove the current tree still passes governance with LLM checks skipped.

## Autonomous Assumptions

- `app/` path scoping is based on normalized path parts so tests can use temporary directories.
- Sync HTTP detection covers direct imports, aliases, module aliases, and common synchronous method calls; it intentionally allows `httpx.AsyncClient`.
- The chat ordering check is targeted to `app/api/v1/chat.py` and `chat_completions()` because that is the visible gateway route.
- Testing strategy: use focused unit tests for rule behavior, then run the full governance CLI with `--skip-llm`; no GUI/manual artifact is needed because this is a non-UI static-analysis change.

## Phase 1: App Sync HTTP AST Rule

### Changes

#### 1. Extend import and call tracking

**File**: `governance/governance/steps/ast_guardrail.py`  
**Action**: modify

- Add constants:
  - `SYNC_HTTP_RULE_ID = "AST004_SYNC_HTTP_CLIENT_IN_APP"`
  - sync method names: `get`, `post`, `put`, `patch`, `delete`, `request`, `stream`
- Add visitor state:
  - module aliases for `httpx` and `requests`
  - imported names from those modules
- Add `visit_Import()` and `visit_ImportFrom()` to track aliases.
- Update `visit_Call()` to call `_check_sync_http_usage()` before `generic_visit()`.
- Emit `Severity.ERROR` findings only when `_is_app_path(self.file_path)` is true.
- Allow `httpx.AsyncClient` and async-only response/type usage.

#### 2. Add sync HTTP unit tests

**File**: `governance/tests/test_steps.py`  
**Action**: modify

- Add helper to create temp files under `tmp_path / "app"`.
- Test `requests.get()` under `app/` fails with `AST004_SYNC_HTTP_CLIENT_IN_APP`.
- Test `httpx.Client()` under `app/` fails with `AST004_SYNC_HTTP_CLIENT_IN_APP`.
- Test `httpx.AsyncClient()` under `app/` passes.
- Test sync `httpx.Client()` outside `app/` passes this new rule.

### Verification

#### Automated

- [x] `cd governance && python3 -m pytest -q tests/test_steps.py` passes.

#### Manual

- [x] autonomous: verified via `python3 -m pytest -q tests/test_steps.py` assertions that app sync usage fails and async app usage passes.

---

## Phase 2: Chat Route Interceptor Ordering Rule

### Changes

#### 1. Add chat route ordering check

**File**: `governance/governance/steps/ast_guardrail.py`  
**Action**: modify

- Add `CHAT_INTERCEPTOR_ORDER_RULE_ID = "AST005_CHAT_INTERCEPTOR_ORDER"`.
- Add `_is_chat_route_path(path: str) -> bool` for `app/api/v1/chat.py`.
- Add helper to find first call line inside `chat_completions()` for:
  - `intercept_outbound_request`
  - `_resolve_provider`
  - `_get_provider_adapter`
  - `chat_completion`
  - `chat_completion_stream`
- Append an `ERROR` finding if interceptor call is missing or if provider-related calls appear before it.

#### 2. Add ordering unit tests

**File**: `governance/tests/test_steps.py`  
**Action**: modify

- Test a synthetic `app/api/v1/chat.py` where provider resolution happens before interception fails with `AST005_CHAT_INTERCEPTOR_ORDER`.
- Test the real `app/api/v1/chat.py` returns no `AST005_CHAT_INTERCEPTOR_ORDER` findings.

### Verification

#### Automated

- [x] `cd governance && python3 -m pytest -q tests/test_steps.py` passes.

#### Manual

- [x] autonomous: verified via `python3 -m pytest -q tests/test_steps.py` assertions that provider-before-interceptor ordering fails and current route ordering passes.

---

## Phase 3: Full Guardrail Verification and PR Prep

### Changes

#### 1. Update plan checkboxes with actual verification

**File**: `thoughts/qrspi/2026-07-20-gov-ast-gateway-rules/plan.md`  
**Action**: modify during implementation

- Check off each command only after it passes.
- Record autonomous notes for manual checks.

#### 2. Write PR draft files

**Files**: `/tmp/pr-drafts/agent5.md`, `/workspace/.pr-drafts/agent5.md`  
**Action**: create/update

- Include title and body.
- Reference Ledger §11.E.1, `architecture_and_roadmap.md`, `design.md`, and `plan.md`.
- Mention QRSPI Autonomous Mode and artifact directory.

### Verification

#### Automated

- [x] `cd governance && PATH="$HOME/.local/bin:$PATH" ai-guardrail run --root .. --skip-llm` passes.
- [x] `git diff -- app/proxy/interceptor.py .github/workflows/ai-guardrail.yml` is empty.
- [x] `git status --short` reviewed; unrelated pre-existing/concurrent changes are present, so commit staging is limited to this task's AST, test, QRSPI, and PR draft files.

#### Manual

- [x] autonomous: verified via `git diff -- app/proxy/interceptor.py .github/workflows/ai-guardrail.yml` that `app/proxy/interceptor.py` is untouched.
- [x] autonomous: verified via `git diff -- app/proxy/interceptor.py .github/workflows/ai-guardrail.yml` that `.github/workflows/ai-guardrail.yml` is untouched.
