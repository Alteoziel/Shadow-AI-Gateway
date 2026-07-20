# Design Discussion

## Current State

- Copyright signatures live in a small JSON database loaded by the Step 5 filter (`governance/governance/steps/copyright_filter.py:20`, `governance/governance/steps/copyright_filter.py:80-83`).
- The current signature database contains one LeetCode teaching snippet and one hardcoded OpenAI key pattern (`governance/governance/signatures/known_snippets.json`).
- Step 6 deterministic quiz generation builds a study guide and multiple-choice questions without requiring an LLM (`governance/governance/steps/comprehension_gate.py:219-318`, `governance/governance/steps/comprehension_gate.py:340-549`).
- The Phase 1 route has provider selection, streaming relay, and 501 checkpoint behavior already scaffolded (`app/api/v1/chat.py:26-37`, `app/api/v1/chat.py:88-111`).
- The interceptor remains a human-owned TODO that raises `NotImplementedError` (`app/proxy/interceptor.py:13-40`).

## Desired End State

- `known_snippets.json` contains at least 3-5 additional protected signatures focused on realistic FastAPI/httpx gateway anti-patterns.
- Deterministic Step 6 quiz generation includes Phase 1 comprehension questions for provider selection, streaming flow, and the HTTP 501 checkpoint.
- Quiz material still teaches that Checkpoint #1 is human-owned.
- Governance tests cover the new quiz generation behavior and at least one new signature.
- `app/proxy/interceptor.py` remains untouched.

## Patterns to Follow

- Keep signatures as simple JSON records with `id`, `description`, and `content`, matching the existing database shape.
- Add deterministic quiz questions in `_make_questions`, matching the local `_q(...)` helper and existing category labels.
- Use `skip_llm=True` tests for quiz generation so CI does not depend on external API keys.
- Extend `governance/tests/test_steps.py` with focused assertions rather than adding new test infrastructure.

## Autonomous Decisions

1. **Signature count and topic mix**: Add five signatures — FastAPI sync upstream call, `httpx.AsyncClient` per chunk, provider hardcoding, catch-all 501 masking, and returning raw upstream SSE bytes. This exceeds the requested minimum and keeps scope focused on FastAPI/httpx gateway anti-patterns.
2. **Quiz insertion point**: Add fixed Phase 1 questions directly to `_make_questions` after the generic flow question. This keeps deterministic generation stable and makes the questions available for every generated pack.
3. **Checkpoint wording**: Reinforce that the human owns Checkpoint #1 in both the existing manual question and a new 501-specific question. Do not rephrase it as optional or agent-fillable.
4. **Test scope**: Add assertions for new quiz IDs/categories and a copyright test using one of the new snippets. Avoid CLI-only tests because `comprehension_gate.run` is the stable generation API.
5. **Interceptor boundary**: Verify with `git diff -- app/proxy/interceptor.py` after implementation and include the result in PR artifacts.

## What We're NOT Doing

- Not implementing `intercept_outbound_request`.
- Not changing provider adapters or route runtime behavior.
- Not changing dashboard grading or Step 7 behavior.
- Not adding an interceptor or proxy feature.
- Not relying on LLM enrichment for required quiz coverage.

## Open Risks

- Copyright similarity matching uses normalized hash overlap and Levenshtein against the beginning of each file, so tests should use an exact new signature to avoid brittle partial-match assumptions.
- Adding always-on quiz questions increases total question count; tests should assert presence rather than exact count.
