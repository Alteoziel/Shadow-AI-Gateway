Title: Add gateway AST governance rules

Body:
## Summary

Implements Ledger §11.E.1 gateway-specific AST governance rules in Step 1. The AST guardrail now blocks synchronous `httpx` / `requests` usage in `app/` while allowing async provider clients, and it verifies that the chat completion route calls `intercept_outbound_request` before provider resolution or provider calls.

## Design Decisions

- Kept the rules in `governance/governance/steps/ast_guardrail.py` because this is structural governance.
- Scoped sync HTTP blocking to `app/` so governance-side synchronous clients remain outside this gateway rule.
- Added stable rule IDs: `AST004_SYNC_HTTP_CLIENT_IN_APP` and `AST005_CHAT_INTERCEPTOR_ORDER`.
- Preserved the human-owned interceptor checkpoint; `app/proxy/interceptor.py` is untouched.

## Changes

- Added AST import/call tracking for sync `httpx` / `requests` calls in app files.
- Added a structural chat route ordering check for `app/api/v1/chat.py`.
- Added unit tests in `governance/tests/test_steps.py`.
- Added QRSPI artifacts under `thoughts/qrspi/2026-07-20-gov-ast-gateway-rules/`.

## How to Verify

- `cd governance && python3 -m pytest -q tests/test_steps.py`
- `cd governance && PATH="$HOME/.local/bin:$PATH" ai-guardrail run --root .. --skip-llm`
- `git diff -- app/proxy/interceptor.py .github/workflows/ai-guardrail.yml`

## References

- Ledger: `architecture_and_roadmap.md` §11.E.1
- QRSPI design: `thoughts/qrspi/2026-07-20-gov-ast-gateway-rules/design.md`
- QRSPI plan: `thoughts/qrspi/2026-07-20-gov-ast-gateway-rules/plan.md`
- QRSPI mode: Autonomous Mode, with no human process gate.
