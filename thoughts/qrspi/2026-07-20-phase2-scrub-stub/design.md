# Design Discussion

## Current State

- The gateway is a Python 3.12 FastAPI app with package discovery for `app*`, so a new `app.scrub` package fits the existing packaging model. `pyproject.toml:1-12`, `pyproject.toml:24-27`
- The active human checkpoint is Phase 1's async interceptor, which intentionally raises `NotImplementedError` and is tested as a blocked product state. `app/proxy/interceptor.py:5-40`, `tests/test_interceptor_contract.py:10-19`
- The chat route imports and invokes only the interceptor before provider forwarding; existing tests verify this route boundary without real upstream calls. `app/api/v1/chat.py:9-12`, `app/api/v1/chat.py:82-116`, `tests/test_proxy_routing.py:25-64`
- The Ledger records Phase 2 as `not_started` and currently uses a TBD path for the scrubbing checkpoint. `architecture_and_roadmap.md:165-172`, `architecture_and_roadmap.md:216-223`

## Desired End State

Create Phase 2 prep scaffolding only:

- `app/scrub/` exists as an importable package.
- `app/scrub/pipeline.py` exposes the human-owned pipeline entrypoint with `TODO: Human Hands-On Implementation`, a 3-bullet cheat sheet including the sub-100ms budget, and `NotImplementedError`.
- Interfaces/types exist for future scrub input/output contracts without performing any detection or redaction.
- A focused test harness asserts the stub raises and documents the latency budget.
- The Ledger points Phase 2 checkpoint file references to `app/scrub/pipeline.py` while Phase 2 remains `not_started` and Checkpoint #1 remains `blocked_on_human`.

## Patterns to Follow

- Follow the interceptor checkpoint placeholder style: async function, explicit human checkpoint comments, cheat sheet, scope notes, and `NotImplementedError`. `app/proxy/interceptor.py:5-40`
- Follow existing package export style with a narrow `__all__` for the new package. `app/proxy/__init__.py:1-5`
- Follow current pytest patterns for asserting stubs and importable async functions. `tests/test_interceptor_contract.py:10-19`
- Follow existing source-inspection tests for route boundary assertions when checking that scrub remains unwired. `tests/test_interceptor_contract.py:21-44`

## Autonomous Decisions

1. **Entrypoint shape**: choose `async def scrub_prompt(request: ScrubRequest) -> ScrubResult` - mirrors async gateway boundaries while staying independent from the interceptor.
2. **Type location**: choose `app/scrub/types.py` with dataclasses and literals - lightweight stdlib contracts avoid adding dependencies or validation behavior.
3. **Checkpoint status**: keep Phase 2 status `not_started` and keep its checkpoint status `not_started` - this branch only records the future human checkpoint path; it does not start Phase 2.
4. **Test scope**: add a focused pytest module that asserts importability, `NotImplementedError`, budget constants, and no chat/interceptor imports - this verifies scaffold boundaries without testing scrub logic.
5. **Export policy**: export only the public contracts and entrypoint from `app/scrub/__init__.py` - matches narrow package boundaries and keeps future internals private.

## Design Decisions

1. **Standalone scrub package**: `app/scrub/` is created but not imported from existing request flow.
2. **Human-owned placeholder**: `app/scrub/pipeline.py` carries the Phase 2 checkpoint TODO and exception exactly where the Ledger points.
3. **Budget as contract**: expose `SCRUB_LATENCY_BUDGET_MS = 100` and test it so future implementation has an obvious target.
4. **No behavior shims**: the pipeline does not return a fake unmodified result because that could accidentally be wired into production flow.

## What We're NOT Doing

- No regex, NLP, tokenization, entity detection, redaction loop, or string substitution logic.
- No imports or calls from `app/proxy/interceptor.py`.
- No imports or calls from `app/api/v1/chat.py`.
- No provider request mutation.
- No Phase 1 interceptor implementation.

## Open Risks

- Future human implementation may choose a different result shape; the dataclass contract should be revisited when Phase 2 actually starts.
- A route-level integration test for scrub is intentionally absent because wiring is explicitly out of scope for this scaffold.
