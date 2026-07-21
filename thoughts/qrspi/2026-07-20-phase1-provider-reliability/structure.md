# Structure Outline

## Approach

Keep the human-owned interceptor checkpoint unchanged while moving provider reliability into provider-owned shared helpers and focused adapter tests. Preserve the existing raw streaming relay, and make Anthropic raw SSE relay an explicit, tested Phase 1 contract.

## Phase 1: Shared Gateway Error Mapping

Introduce reusable provider helpers for credential validation and `httpx` exception translation, then cover them through provider behavior tests.

**Files**: `app/proxy/providers/base.py`, `tests/test_provider_reliability.py`

**Key changes**:
- `ProviderGatewayError` or helper functions in `base.py` — converts provider/config/upstream failures into `fastapi.HTTPException`.
- `require_api_key(provider_name: str, api_key: str) -> str` — rejects missing/blank keys before headers are built.
- `map_httpx_error(provider_name: str, exc: httpx.HTTPError) -> HTTPException` — maps status errors, timeouts, and request errors.

**Verify**: `pytest tests/test_provider_reliability.py` passes for missing keys and error mapping helper/provider behavior.

---

## Phase 2: OpenAI Adapter Reliability

Wrap OpenAI non-streaming and streaming setup calls with the shared helpers. Streaming should call `raise_for_status()` before returning the open response.

**Files**: `app/proxy/providers/openai.py`, `tests/test_provider_reliability.py`

**Key changes**:
- `OpenAIProvider._headers() -> dict[str, str]` — uses `require_api_key("openai", self._api_key)`.
- `OpenAIProvider.chat_completion(payload: dict[str, Any]) -> dict[str, Any]` — catches `httpx` failures and raises mapped `HTTPException`.
- `OpenAIProvider.chat_completion_stream(payload: dict[str, Any]) -> httpx.Response` — catches setup/status failures and returns only successful streaming responses.

**Verify**: OpenAI tests cover missing key, upstream 4xx/5xx, timeout, request error, and streaming status error without real network calls.

---

## Phase 3: Anthropic Adapter Reliability and Raw Streaming Contract

Wrap Anthropic non-streaming and streaming setup calls with the shared helpers and document/test that streaming remains raw Anthropic SSE relay in Phase 1.

**Files**: `app/proxy/providers/anthropic.py`, `app/proxy/streaming.py`, `tests/test_provider_reliability.py`, `tests/test_streaming.py`

**Key changes**:
- `AnthropicProvider._headers() -> dict[str, str]` — uses `require_api_key("anthropic", self._api_key)`.
- `AnthropicProvider.chat_completion(payload: dict[str, Any]) -> dict[str, Any]` — catches mapped `httpx` failures.
- `AnthropicProvider.chat_completion_stream(payload: dict[str, Any]) -> httpx.Response` — catches setup/status failures, returns only successful raw Anthropic SSE responses.
- `relay_sse_stream(...)` docstring/comment — explicitly states it relays provider bytes unchanged; Anthropic normalization is not performed here.

**Verify**: Anthropic tests cover missing key, upstream status mapping, timeout/request mapping, streaming status mapping, and raw SSE bytes preserved by relay.

---

## Phase 4: Route and Checkpoint Regression

Run existing route and interceptor tests plus focused provider tests to prove the checkpoint contract remains untouched and provider reliability works after integration.

**Files**: `tests/test_proxy_routing.py`, `tests/test_interceptor_contract.py`, `app/proxy/interceptor.py`

**Key changes**:
- No interceptor implementation changes.
- Existing tests should remain green.
- If needed, add route-level test coverage only for provider-raised `HTTPException` propagation after the interceptor is patched in the test.

**Verify**: `pytest tests/test_provider_reliability.py tests/test_streaming.py tests/test_proxy_routing.py tests/test_interceptor_contract.py` passes; `git diff -- app/proxy/interceptor.py` is empty.

## Testing Checkpoints

- After Phase 1, missing keys and raw `httpx` failures have deterministic HTTP status/detail behavior in focused tests.
- After Phase 2, OpenAI adapter behavior is reliable for both streaming setup and non-streaming calls.
- After Phase 3, Anthropic adapter behavior matches OpenAI reliability while preserving and testing raw streaming relay.
- After Phase 4, existing Checkpoint #1 / 501 tests still pass and the interceptor file is unchanged.
