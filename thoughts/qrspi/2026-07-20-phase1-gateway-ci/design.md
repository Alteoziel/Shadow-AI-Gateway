# Design Discussion

## Current State

- The Phase 1 gateway route already calls `intercept_outbound_request` before provider selection and payload construction, and converts the checkpoint `NotImplementedError` to HTTP 501.
- Existing tests protect the active checkpoint by asserting the interceptor is async, still raises `NotImplementedError`, and appears before provider usage in `app/api/v1/chat.py`.
- Existing unlock-path coverage patches the interceptor and provider to show provider routing resumes after the human fills Checkpoint #1.
- Provider adapters contain meaningful behavior that is currently untested: Anthropic payload mapping, OpenAI and Anthropic HTTP request construction, streaming request construction, and Anthropic response conversion.
- Streaming relay cleanup behavior is encoded in `app/proxy/streaming.py` but currently has no direct test coverage.
- CI currently runs governance from `governance/`; no independent app pytest workflow exists.

## Desired End State

The repository has a focused gateway test matrix that proves the Phase 1 contract around Checkpoint #1 without filling the checkpoint. CI runs root app tests independently from governance, and the existing 501/`NotImplementedError` expectations remain intact.

## Autonomous Decisions

1. **Where should the new tests live?** Choose root `tests/` files, not a new app-local test package, because root pytest config already points to `tests` and existing gateway tests live there.
2. **How should upstream HTTP calls be mocked?** Use `respx` for provider adapter tests because it integrates directly with `httpx` and lets tests assert exact request JSON without real network calls.
3. **How should route helper behavior be tested?** Import and test `_resolve_provider` and `_build_upstream_payload` directly because they are stable route-local boundaries and avoid invoking the unimplemented checkpoint.
4. **How should streaming relay be tested?** Use an `httpx.MockTransport` streaming response and consume the returned `StreamingResponse` iterator so cleanup behavior is observed without a live server.
5. **How should CI be scoped?** Add `.github/workflows/gateway-ci.yml` that installs the root package with dev dependencies and runs `pytest -q tests`, leaving governance CI unchanged.

## Design Decisions

1. **Additive test-only change**: Only add gateway tests, dev dependency support, and app CI; no production behavior changes.
2. **Checkpoint-preserving coverage**: Keep `tests/test_interceptor_contract.py` and the 501 test intact; new unlock-path tests continue to mock the interceptor.
3. **HTTPX-native mocks**: Add `respx` as a root dev dependency for provider adapter tests.
4. **Independent CI**: Use a separate workflow name/job for gateway pytest so app failures are visible independently from governance.
5. **Narrow assertions**: Assert payloads, headers where useful, cleanup calls, and route helper contracts without testing third-party SDK behavior.

## What We're NOT Doing

- Not implementing or modifying `app/proxy/interceptor.py`.
- Not adding scrubbing, audit logging, database writes, Terraform, or deployment changes.
- Not changing provider adapter runtime behavior unless a test exposes a bug that already violates the intended Phase 1 contract.
- Not weakening the existing checkpoint contract tests or 501 expectations.
- Not merging gateway CI into `.github/workflows/ai-guardrail.yml`.

## Open Risks

- `respx` is a new dev dependency, so lockfile-free installation depends on current package availability.
- Direct testing of underscored route helpers couples tests to route module boundaries, but those helpers are the clearest existing units for provider selection and payload construction.
- Streaming cleanup tests must consume the response body; otherwise the relay's `finally` path will not execute.
