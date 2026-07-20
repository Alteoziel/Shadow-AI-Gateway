# Structure Outline

## Approach

Extend the existing AST guardrail with gateway-specific rules that inspect only relevant app files, then cover those rules with direct unit tests and full guardrail verification. Keep the workflow and interceptor checkpoint untouched.

## Phase 1: App Sync HTTP AST Rule

Add path-aware AST detection for synchronous `httpx` / `requests` usage under `app/`, while preserving allowed async `httpx.AsyncClient` usage.

**Files**: `governance/governance/steps/ast_guardrail.py`, `governance/tests/test_steps.py`

**Key changes**:

- `_is_app_path(path: str) -> bool` — new helper for path scoping.
- `_ImportTracker` fields on `_StructureVisitor` — track `httpx`, `requests`, and imported sync HTTP call aliases.
- `_check_sync_http_usage(node: ast.Call) -> None` — new visitor helper emitting `AST004_SYNC_HTTP_CLIENT_IN_APP`.
- Tests for `requests.get`, `httpx.Client`, and allowed `httpx.AsyncClient` under simulated `app/` paths.

**Verify**: `cd governance && pytest -q tests/test_steps.py` passes.

---

## Phase 2: Chat Route Interceptor Ordering Rule

Add a targeted structural check for `app/api/v1/chat.py` ensuring `chat_completions()` calls `intercept_outbound_request` before provider resolution, adapter construction, or provider chat calls.

**Files**: `governance/governance/steps/ast_guardrail.py`, `governance/tests/test_steps.py`

**Key changes**:

- `_check_chat_route_interceptor_order(tree: ast.AST, file_path: str) -> list[Finding]` — new file-level check.
- `_first_call_line(function: ast.AST, names: set[str]) -> int | None` — helper for first call locations.
- `analyze_file(path: Path) -> list[Finding]` — append route ordering findings after visitor findings.
- Tests for bad ordering and current route compliance.

**Verify**: `cd governance && pytest -q tests/test_steps.py` passes.

---

## Phase 3: Full Guardrail Verification and PR Prep

Run the complete governance suite with LLM skipped, update QRSPI checkboxes, commit, push, and write draft PR files.

**Files**: `thoughts/qrspi/2026-07-20-gov-ast-gateway-rules/plan.md`, `/tmp/pr-drafts/agent5.md`, `/workspace/.pr-drafts/agent5.md`

**Key changes**:

- Plan verification checkboxes record exact commands and results.
- Draft PR body references Ledger §11.E.1 and QRSPI artifacts.

**Verify**: `cd governance && ai-guardrail run --root .. --skip-llm` passes; `git diff -- app/proxy/interceptor.py .github/workflows/ai-guardrail.yml` is empty.

## Testing Checkpoints

- After Phase 1, new app sync HTTP violations fail AST guardrail and async provider clients remain allowed.
- After Phase 2, chat-route provider-before-interceptor regressions fail AST guardrail and the current route remains green.
- After Phase 3, unit tests and full `ai-guardrail --skip-llm` are green on the branch.
