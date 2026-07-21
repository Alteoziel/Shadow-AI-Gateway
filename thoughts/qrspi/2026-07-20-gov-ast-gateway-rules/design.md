# Design Discussion

## Current State

- The governance pipeline runs `ast_guardrail.run(paths)` as Step 1 and marks the pipeline failed when any non-skipped step fails. (`governance/governance/pipeline.py:109-151`)
- AST findings use `Finding` and `StepResult`, with `ERROR` and `CRITICAL` severities counted as blocking. (`governance/governance/models.py:18-52`)
- The current AST guardrail parses each Python file with `ast.parse()`, visits structure nodes, and emits rule IDs `AST000` through `AST003`. (`governance/governance/steps/ast_guardrail.py:10-159`)
- Governance tests already assert step results directly with temporary Python files and `rule_id` checks. (`governance/tests/test_steps.py:15-48`)
- The chat route currently awaits `intercept_outbound_request()` before resolving or constructing provider adapters. (`app/api/v1/chat.py:89-101`)
- `app/proxy/interceptor.py` is a human checkpoint and raises `NotImplementedError`. (`app/proxy/interceptor.py:4-39`)
- App providers use `httpx.AsyncClient`, while governance modules use synchronous `httpx.Client`. (`app/proxy/providers/openai.py:14-49`, `app/proxy/providers/anthropic.py:15-128`, `governance/governance/steps/security_auditor.py:112-119`)

## Desired End State

- AST governance flags synchronous `httpx` / `requests` usage only under `app/`.
- AST governance includes a structural check that the chat completion route calls the interceptor before provider resolution or provider invocation.
- Existing allowed async app provider usage remains green.
- Unit tests under `governance/tests/` cover both new rules.
- `ai-guardrail run --skip-llm` remains green on the current tree.
- `.github/workflows/ai-guardrail.yml` and `app/proxy/interceptor.py` remain unchanged.

## Patterns to Follow

- Keep rule implementation inside `governance/governance/steps/ast_guardrail.py`, matching existing AST visitor and `Finding` creation patterns. (`governance/governance/steps/ast_guardrail.py:23-159`)
- Use stable `rule_id` assertions in unit tests, matching existing AST tests. (`governance/tests/test_steps.py:15-48`)
- Treat `ERROR` findings as blocking for governance failures. (`governance/governance/pipeline.py:135-151`)
- Avoid regex-only source scanning for AST rules where node identity and call ordering can be parsed structurally. (`governance/governance/steps/ast_guardrail.py:121-138`)

## Autonomous Decisions

1. **Scope of sync HTTP rule**: Restrict to paths under `app/` — this matches the gateway-specific requirement and avoids flagging governance's own synchronous admin/client calls.
2. **Rule severity**: Use `ERROR` for new gateway governance violations — the pipeline treats errors as blocking while leaving critical severity for arbitrary-code execution.
3. **HTTP detection style**: Track imports and aliases with AST, then flag synchronous `httpx.Client`, `httpx.get/post/request`, `requests.*`, and imported equivalents while explicitly allowing `httpx.AsyncClient`.
4. **Chat ordering check**: Implement a structural order check in `app/api/v1/chat.py` for `chat_completions()` — source already has a single route function and visible ordering.
5. **Test placement**: Add focused tests to `governance/tests/test_steps.py` — the file already hosts AST step tests and uses `tmp_path` fixtures.

## Design Decisions

1. **Extend AST step, not security auditor**: The requested behavior is structural AST governance, and Step 1 already owns code-structure checks.
2. **Use new rule IDs**: Add `AST004_SYNC_HTTP_CLIENT_IN_APP` and `AST005_CHAT_INTERCEPTOR_ORDER` so tests and reports can distinguish these gateway rules.
3. **Path-aware checks**: Determine `app/` membership from normalized path parts, so temporary test files can simulate `tmp_path/app/...`.
4. **No interceptor implementation**: The structural check may read chat route source, but no code is added to `app/proxy/interceptor.py`.

## What We're NOT Doing

- Not editing or implementing `app/proxy/interceptor.py`.
- Not disabling or weakening `.github/workflows/ai-guardrail.yml`.
- Not banning async `httpx.AsyncClient` app usage.
- Not broadening the rule to non-app governance modules.
- Not adding runtime request behavior.

## Open Risks

- Import alias handling must be broad enough for common sync client shapes without becoming a full data-flow engine.
- The chat route order check should be strict enough to catch regressions but scoped enough not to require route refactoring.
