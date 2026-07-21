# Implementation Plan

## Overview

Improve provider reliability by validating server-side provider credentials before upstream calls, mapping upstream `httpx` failures into clear gateway `HTTPException`s, and making Anthropic raw streaming relay an explicit tested Phase 1 contract. Keep `app/proxy/interceptor.py` unchanged and preserve the existing 501 checkpoint behavior.

## Testing Strategy

- Automated focused tests are the right evidence because this is provider/error-path behavior and can be exercised without a GUI or live provider keys.
- Run focused provider/streaming/proxy/interceptor tests after implementation.
- Run the full gateway test suite (`pytest tests`) before commit.
- Confirm `git diff -- app/proxy/interceptor.py` is empty before commit and before final summary.

## Phase 1: Shared Gateway Error Mapping

### Changes

#### 1. Shared provider helpers
**File**: `app/proxy/providers/base.py`  
**Action**: modify

Add FastAPI/httpx imports and helper functions:

- `require_api_key(provider_name: str, api_key: str) -> str`
  - Strip whitespace.
  - If blank, raise `HTTPException(status_code=500, detail={"error": "provider_configuration_error", "provider": provider_name, "message": f"{provider_name} API key is not configured"})`.
  - Return stripped key.
- `map_httpx_error(provider_name: str, exc: httpx.HTTPError) -> HTTPException`
  - `HTTPStatusError` -> HTTP 502 detail with `error: "upstream_http_error"`, `provider`, `upstream_status_code`, and short message.
  - `TimeoutException` -> HTTP 504 detail with `error: "upstream_timeout"`.
  - `RequestError` -> HTTP 502 detail with `error: "upstream_request_error"`.
  - generic `HTTPError` -> HTTP 502 detail with `error: "upstream_error"`.

#### 2. Provider reliability tests
**File**: `tests/test_provider_reliability.py`  
**Action**: create

Add async tests using `httpx.MockTransport` by replacing each provider's `_client` after construction. Cover:

- Missing/blank OpenAI key raises HTTP 500 before request.
- HTTP status error maps to HTTP 502 with upstream status.
- Timeout maps to HTTP 504.
- Request/network error maps to HTTP 502.
- Streaming status error maps to HTTP 502 during setup.

### Verification

#### Automated
- [x] `python3 -m pytest tests/test_provider_reliability.py` passes.

#### Manual
- [x] `autonomous: verified provider helper details contain no key/payload leakage by inspecting assertions and failure output.`

---

## Phase 2: OpenAI Adapter Reliability

### Changes

#### 1. OpenAI provider wrapping
**File**: `app/proxy/providers/openai.py`  
**Action**: modify

- Import `HTTPException` helper functions from `base.py`.
- In `_headers`, call `require_api_key("openai", self._api_key)` and use the returned key.
- In `chat_completion`, wrap the POST/`raise_for_status`/JSON sequence in `try/except httpx.HTTPError as exc: raise map_httpx_error("openai", exc) from exc`.
- In `chat_completion_stream`, build/send the stream request in the same try block, call `response.raise_for_status()` before returning, and close the response before raising if status validation fails after response creation.

### Verification

#### Automated
- [x] `python3 -m pytest tests/test_provider_reliability.py -k openai` passes.

#### Manual
- [x] `autonomous: verified OpenAI streaming tests assert setup errors are HTTPExceptions, not raw streamed provider bodies.`

---

## Phase 3: Anthropic Adapter Reliability and Raw Streaming Contract

### Changes

#### 1. Anthropic provider wrapping
**File**: `app/proxy/providers/anthropic.py`  
**Action**: modify

- Import provider helper functions from `base.py`.
- In `_headers`, call `require_api_key("anthropic", self._api_key)` and use the returned key.
- In `chat_completion`, wrap POST/`raise_for_status`/JSON/OpenAI-shape conversion in mapped `httpx.HTTPError` handling.
- In `chat_completion_stream`, wrap send/status validation similarly and close a failed streaming response before raising.

#### 2. Raw relay documentation
**File**: `app/proxy/streaming.py`  
**Action**: modify

- Update `relay_sse_stream` docstring to state it relays provider bytes unchanged.
- Note that Anthropic streaming remains raw Anthropic SSE in Phase 1; provider-specific normalization must happen before this helper if added later.

#### 3. Streaming tests
**File**: `tests/test_anthropic_streaming_contract.py`  
**Action**: create

- Add an async test that builds an `httpx.Response` with Anthropic SSE bytes, passes it to `relay_sse_stream`, and consumes `response.body_iterator`.
- Assert output bytes exactly equal the original Anthropic SSE bytes.

### Verification

#### Automated
- [x] `python3 -m pytest tests/test_provider_reliability.py -k anthropic` passes.
- [x] `python3 -m pytest tests/test_anthropic_streaming_contract.py` passes.

#### Manual
- [x] `autonomous: verified the docstring and test explicitly call out raw Anthropic SSE relay.`

---

## Phase 4: Route and Checkpoint Regression

### Changes

#### 1. Optional route propagation test
**File**: `tests/test_proxy_routing.py`  
**Action**: modify only if focused provider tests leave route-level behavior unproven.

- Patch interceptor to return normalized payload.
- Patch provider to raise a FastAPI `HTTPException`.
- Assert the route returns the provider status/detail.

#### 2. Interceptor protection
**File**: `app/proxy/interceptor.py`  
**Action**: do not modify

- Confirm no diff exists.

### Verification

#### Automated
- [x] `python3 -m pytest tests/test_provider_reliability.py tests/test_anthropic_streaming_contract.py tests/test_proxy_routing.py tests/test_interceptor_contract.py` passes.
- [x] `python3 -m pytest tests` passes.
- [x] `git diff -- app/proxy/interceptor.py` has no output.

#### Manual
- [x] `autonomous: verified the 501 route test still asserts Checkpoint #1 and intercept_outbound_request text.`

## Implementation Notes

- Deviated from the original `tests/test_streaming.py` filename because the working tree contained unrelated untracked streaming tests. The raw Anthropic relay test was placed in `tests/test_anthropic_streaming_contract.py` so this package can be staged independently.

## Autonomous Assumptions

- Missing API keys are server configuration failures and should use HTTP 500.
- Upstream 4xx and 5xx are mapped to HTTP 502 rather than mirrored as client-facing status codes.
- Anthropic streaming is intentionally raw relay for this package; OpenAI SSE normalization is not implemented here.
- No external provider calls should be made during tests.
