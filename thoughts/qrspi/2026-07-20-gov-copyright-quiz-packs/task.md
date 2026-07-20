# Task

Grow the governance copyright signature database and Phase 1 comprehension quiz packs for the Shadow AI Guardrail Gateway. The change must add FastAPI/httpx-oriented protected signatures, teach provider selection, streaming, and HTTP 501 checkpoint behavior, preserve the rule that Checkpoint #1 is human-owned, and avoid implementing `app/proxy/interceptor.py`.

## Scope Boundaries

- Add governance data, deterministic quiz generation content, tests, QRSPI artifacts, and PR draft files.
- Do not implement the interceptor.
- Do not soften the Ledger rule that Checkpoint #1 belongs to the human.

## Context Isolation Note

This run is itself operating as a parent-managed subagent. The system reminder forbids spawning additional subagents unless requested by instructions; QRSPI requires isolation, so this run records each stage as a separate disk artifact and constrains later implementation to `plan.md` as the working input.

## Rejected Alternate Framings

- "General quiz cleanup" was rejected because the task specifically asks for Phase 1 provider/streaming/501 quiz packs.
- "LeetCode signature expansion" was rejected because the task explicitly asks for FastAPI/httpx anti-patterns, not LeetCode-only coverage.
