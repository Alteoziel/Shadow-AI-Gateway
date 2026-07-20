# Structure Outline

## Approach

Add tests around the existing gateway boundaries that sit after or around Human Checkpoint #1, then add an app-only CI workflow that runs those tests from the root package. The interceptor remains a failing checkpoint by design.

## Phase 1: Gateway Behavior Test Matrix

This phase proves provider selection, upstream payload construction, Anthropic mapping, provider HTTP requests, streaming setup, relay cleanup, and unlock-path routing through mocks.

**Files**: `pyproject.toml`, `tests/test_proxy_provider_selection.py`, `tests/test_gateway_payloads.py`, `tests/test_provider_adapters.py`, `tests/test_streaming_relay.py`

**Key changes**:

- `dev = [...]` — add `respx` for HTTPX request mocking.
- `test_resolve_provider_uses_request_override_and_default_env()` — verifies route provider resolution.
- `test_build_upstream_payload_protects_interceptor_fields()` — verifies upstream payload merge precedence.
- `test_anthropic_payload_maps_system_messages_and_stop_sequences()` — verifies Anthropic request mapping.
- `test_openai_provider_posts_payload_with_auth_headers()` — verifies OpenAI non-streaming HTTP call.
- `test_anthropic_provider_posts_mapped_payload_and_returns_openai_shape()` — verifies Anthropic non-streaming adapter behavior.
- `test_provider_streaming_requests_send_stream_true()` — verifies streaming payload construction.
- `test_relay_sse_stream_yields_chunks_filters_headers_and_cleans_up()` — verifies relay body, headers, and cleanup.
- `tests/test_proxy_provider_selection.py` verifies provider selection can choose Anthropic after the interceptor is mocked.

**Verify**: `python -m pytest tests -q` passes; `git diff -- app/proxy/interceptor.py tests/test_interceptor_contract.py` shows no weakening of checkpoint code or contract tests.

---

## Phase 2: Gateway CI Workflow

This phase adds a GitHub Actions workflow that runs app pytest independently of the governance workflow.

**Files**: `.github/workflows/gateway-ci.yml`

**Key changes**:

- `name: Gateway CI` — workflow for root app tests.
- `pip install -e ".[dev]"` — install app and test dependencies.
- `python -m pytest tests -q` — run only gateway tests.

**Verify**: `python -m pytest tests -q` passes locally; workflow file is syntactically simple YAML and does not modify governance CI.

## Testing Checkpoints

- After Phase 1, local pytest proves the gateway behavior matrix and current checkpoint 501 behavior.
- After Phase 2, local pytest still passes and app CI exists separately from `.github/workflows/ai-guardrail.yml`.
- Before final push, confirm `app/proxy/interceptor.py` still raises `NotImplementedError`.
