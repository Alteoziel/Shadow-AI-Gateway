# Design Discussion

## Current State

- The chat route invokes `intercept_outbound_request` before selecting or calling providers, and maps its `NotImplementedError` to HTTP 501 (`app/api/v1/chat.py:80-100`; research Q1).
- The interceptor remains the active human checkpoint and raises `NotImplementedError` from a `TODO: Human Hands-On Implementation` block (`app/proxy/interceptor.py:11-40`; research Q1/Q5).
- OpenAI and Anthropic providers own upstream URL/header/payload details and use `httpx.AsyncClient` with the same timeout shape (`app/proxy/providers/openai.py:12-49`, `app/proxy/providers/anthropic.py:12-129`; research Q2).
- Missing API keys currently become empty `Authorization` / `x-api-key` header values because settings default to empty strings and providers do not validate them (`app/config.py:17-18`; research Q3).
- Non-streaming provider calls use `raise_for_status()` and let raw `httpx` exceptions propagate; streaming calls return raw upstream responses without status normalization (`app/proxy/providers/openai.py:24-46`, `app/proxy/providers/anthropic.py:70-97`; research Q2).
- Streaming relay forwards upstream bytes/status/headers unchanged except hop-by-hop headers, so Anthropic streaming is currently a raw Anthropic SSE relay while Anthropic non-streaming is OpenAI-shaped (`app/proxy/streaming.py:7-38`; research Q4).
- Tests assert the interceptor stays async, raises `NotImplementedError`, and the route returns 501 while Checkpoint #1 is incomplete (`tests/test_interceptor_contract.py:10-45`, `tests/test_proxy_routing.py:16-22`; research Q5).

## Desired End State

Provider failures should appear as clear gateway `HTTPException`s instead of raw tracebacks. Missing or blank provider keys should fail before any upstream request. Upstream `httpx` 4xx/5xx, timeout, and request errors should map to stable gateway errors for both streaming setup and non-streaming calls. Anthropic streaming behavior should be intentional and tested; for Phase 1, document and test the existing raw relay instead of inventing a streaming transformer.

Verification should include focused provider tests and existing route/interceptor contract tests. The interceptor body must remain untouched.

## Autonomous Decisions

1. **Where to map provider errors?**  
   Chosen: provider adapter layer via shared helpers in `app/proxy/providers/base.py`.  
   Rationale: providers already own upstream `httpx` calls and credentials, while the route only selects adapters and response types (research Q1/Q2). A shared provider error mapper keeps OpenAI and Anthropic behavior consistent without adding route-level `except Exception` catch-alls that could hide checkpoint behavior.

2. **Status code mapping for upstream HTTP errors?**  
   Chosen: map upstream 4xx/5xx to HTTP 502 gateway errors with provider/upstream status in the response detail.  
   Rationale: the gateway is failing to satisfy the client because an upstream provider rejected or failed the request. Preserving the upstream status in structured detail gives clear diagnostics without proxying provider-specific error bodies as the gateway's own status contract.

3. **Status code mapping for timeouts and request/network errors?**  
   Chosen: map `httpx.TimeoutException` to HTTP 504 and other `httpx.RequestError` to HTTP 502.  
   Rationale: timeout is a gateway timeout from the client perspective; other transport errors are upstream gateway failures. This directly covers the task's timeout and 4xx/5xx goals.

4. **Missing API key behavior?**  
   Chosen: validate key presence in each provider before building request headers, raising HTTP 500 with a provider-specific configuration message.  
   Rationale: provider keys are server-side configuration, not client input. The failure should be clear and should happen before any upstream bytes are sent.

5. **Anthropic streaming shape?**  
   Chosen: document and test intentional raw Anthropic SSE relay for Phase 1.  
   Rationale: non-streaming Anthropic conversion already exists, but robust streaming conversion requires parsing multiple Anthropic event types and assembling OpenAI chat chunk deltas. That is a larger behavioral contract than this reliability package needs. The current relay helper already forwards raw bytes; adding tests/documentation makes it explicit.

## Patterns to Follow

- Keep route-level checkpoint handling intact: catch only `NotImplementedError` from the interceptor and raise the existing 501 detail (`app/api/v1/chat.py:88-97`; research Q1).
- Keep provider-specific URL/header/payload logic inside provider classes (`app/proxy/providers/openai.py:12-49`, `app/proxy/providers/anthropic.py:12-129`; research Q2).
- Use `HTTPException` for gateway-facing errors, matching the route's existing unsupported-provider and checkpoint behavior (`app/api/v1/chat.py:31-37`, `app/api/v1/chat.py:88-97`; research Q1).
- Preserve `relay_sse_stream` raw byte relay behavior unless a provider deliberately returns a normalized OpenAI stream (`app/proxy/streaming.py:7-38`; research Q4).
- Add focused tests alongside existing proxy/interceptor tests because no provider-specific reliability tests exist yet (research Q5).

## Design Decisions

1. **Shared provider reliability helpers**: Add a provider-facing exception class/helper functions in `app/proxy/providers/base.py` that validate credentials and translate `httpx` errors to FastAPI `HTTPException`s.
2. **Provider adapters wrap every upstream setup call**: OpenAI and Anthropic non-streaming and streaming setup calls should call the shared mapper. Streaming errors must be mapped before the route starts `StreamingResponse`.
3. **Streaming status normalization**: Streaming provider setup should call `raise_for_status()` before returning the upstream response, so error responses become gateway JSON errors instead of relayed provider error bodies.
4. **Anthropic raw streaming contract**: Add a docstring/comment and tests showing Anthropic streaming returns raw Anthropic SSE bytes through the gateway relay path.
5. **Focused test coverage**: Add provider unit tests for missing keys, upstream status errors, timeouts, request errors, streaming status errors, and Anthropic raw streaming relay behavior. Keep existing interceptor tests green.

## What We're NOT Doing

- Not implementing `app/proxy/interceptor.py` or any `TODO: Human Hands-On Implementation`.
- Not adding Phase 2 scrubbing, DB audit logging, or any Checkpoint #1 validation/normalization logic.
- Not introducing new dependencies.
- Not changing the public request schema beyond reliability behavior.
- Not transforming Anthropic streaming into OpenAI SSE in this package.
- Not changing deployment or Vercel/Fly/Render configuration.

## Open Risks

- Provider error detail must avoid leaking secrets or full upstream payloads. Keep details concise: provider, upstream status where applicable, and a short message.
- Tests that use `httpx.AsyncClient` internals should avoid real network access and should be stable against `httpx` minor behavior.
- HTTP 500 for missing server config is intentionally a server configuration error; reviewers may prefer 503, but 500 is clearer for broken deployment configuration.
