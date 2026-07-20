# Research Findings

## Q1: How does the chat completions route currently sequence request validation, interception, provider selection, payload construction, and response handling?

### Findings

- The gateway route accepts `ChatCompletionRequest` through FastAPI/Pydantic at `app/api/v1/chat.py:82`, with the request model defined in `app/models/schemas.py:11`.
- The route serializes the parsed request to `raw_body` and captures request headers before interception at `app/api/v1/chat.py:85`.
- `intercept_outbound_request` is awaited before provider resolution, adapter creation, or payload building at `app/api/v1/chat.py:89`.
- `NotImplementedError` from the interceptor is converted to HTTP 501 with `CHECKPOINT_501_DETAIL` at `app/api/v1/chat.py:94`.
- Provider resolution reads request override first and then default settings at `app/api/v1/chat.py:26`.
- Adapter construction maps `openai` and `anthropic` to concrete provider classes and raises HTTP 400 for unsupported provider names at `app/api/v1/chat.py:31`.
- `_build_upstream_payload` merges `extra_body`, optional gateway fields, normalized metadata, and protected fields at `app/api/v1/chat.py:40`.
- Non-streaming responses call `provider.chat_completion(payload)`, return `JSONResponse`, and close the provider in a `finally` block at `app/api/v1/chat.py:113`.
- Streaming responses call `provider.chat_completion_stream(payload)` and pass the upstream response to `relay_sse_stream` with `provider.aclose` as completion cleanup at `app/api/v1/chat.py:103`.

## Q2: What provider adapter behavior exists for OpenAI and Anthropic, including request payload transformation, headers, non-streaming calls, streaming calls, and response shape conversion?

### Findings

- `BaseLLMProvider` defines async methods for non-streaming completion, streaming completion, and cleanup at `app/proxy/providers/base.py:7`.
- `OpenAIProvider` sends gateway payloads directly to `https://api.openai.com/v1/chat/completions` at `app/proxy/providers/openai.py:7`.
- OpenAI headers include bearer auth and JSON content type at `app/proxy/providers/openai.py:17`.
- OpenAI non-streaming uses `AsyncClient.post(..., json=payload)`, raises for status, and returns response JSON at `app/proxy/providers/openai.py:24`.
- OpenAI streaming creates a copy with `"stream": True`, builds a POST request, and sends it with `stream=True` at `app/proxy/providers/openai.py:33`.
- `AnthropicProvider` maps OpenAI-shaped gateway payloads to the Anthropic Messages API at `app/proxy/providers/anthropic.py:27`.
- Anthropic headers include `x-api-key`, `anthropic-version`, and JSON content type at `app/proxy/providers/anthropic.py:18`.
- Anthropic system messages are joined into a top-level `system` field; user and assistant messages are retained; unsupported roles are skipped at `app/proxy/providers/anthropic.py:30`.
- Anthropic payloads always include `model`, `messages`, and `max_tokens`, with optional `temperature`, `top_p`, and `stop_sequences` at `app/proxy/providers/anthropic.py:51`.
- Anthropic non-streaming posts the mapped payload and converts the response to OpenAI-compatible chat completion shape at `app/proxy/providers/anthropic.py:70`.
- Anthropic streaming adds `"stream": True` to the mapped payload and sends a streaming POST request at `app/proxy/providers/anthropic.py:81`.
- Anthropic response conversion concatenates text blocks, preserves model, maps stop reason, and derives token usage totals at `app/proxy/providers/anthropic.py:100`.

## Q3: How does the gateway relay streaming upstream responses, and what lifecycle or cleanup behavior is currently encoded?

### Findings

- `relay_sse_stream` accepts an `httpx.Response`, default media type `text/event-stream`, and optional async `on_complete` callback at `app/proxy/streaming.py:7`.
- The relay yields raw upstream bytes from `upstream.aiter_bytes()` without buffering the whole body at `app/proxy/streaming.py:20`.
- The relay always awaits `upstream.aclose()` in `finally` and then awaits `on_complete` when supplied at `app/proxy/streaming.py:24`.
- The returned `StreamingResponse` preserves upstream status code and filters hop-by-hop or length headers at `app/proxy/streaming.py:28`.
- `iter_sse_lines` also exists and yields decoded lines from `upstream.aiter_lines()` at `app/proxy/streaming.py:41`.

## Q4: What tests currently exercise health, checkpoint behavior, routing, and the post-checkpoint unlock path?

### Findings

- `tests/test_health.py` verifies `GET /health` returns status 200 and `{"status": "ok"}` at `tests/test_health.py:7`.
- `tests/test_interceptor_contract.py` verifies `intercept_outbound_request` is callable and async at `tests/test_interceptor_contract.py:9`.
- `tests/test_interceptor_contract.py` verifies the interceptor currently raises `NotImplementedError` containing `Checkpoint #1` at `tests/test_interceptor_contract.py:16`.
- `tests/test_interceptor_contract.py` parses `app/api/v1/chat.py` and asserts the route references `intercept_outbound_request` before provider-related hints at `tests/test_interceptor_contract.py:22`.
- `tests/test_proxy_routing.py` verifies the real chat endpoint returns HTTP 501 while the interceptor is not implemented at `tests/test_proxy_routing.py:16`.
- `tests/test_proxy_routing.py` patches the interceptor to return a normalized payload and patches `OpenAIProvider` to prove the route delegates to a provider after the checkpoint unlocks at `tests/test_proxy_routing.py:26`.

## Q5: What project dependency and CI conventions currently exist for app tests versus governance tests?

### Findings

- Root `pyproject.toml` declares Python `>=3.12`, FastAPI, Uvicorn, httpx, and pydantic-settings for the gateway at `pyproject.toml:1`.
- Root dev dependencies currently include `pytest`, `pytest-asyncio`, and `httpx` at `pyproject.toml:14`.
- Root pytest config sets `asyncio_mode = "auto"` and test path `tests` at `pyproject.toml:28`.
- The only existing GitHub workflow is governance-focused and runs from the `governance` working directory at `.github/workflows/ai-guardrail.yml:14`.
- The governance workflow installs `governance` with its dev dependencies and runs `pytest -q` there at `.github/workflows/ai-guardrail.yml:32`.
- The Ledger target layout expects `.github/workflows/ai-guardrail.yml` for the governance pre-merge gate and `tests/` for gateway tests at `architecture_and_roadmap.md:314`.

## Cross-Cutting Observations

- The active checkpoint file is `app/proxy/interceptor.py`, owned by the human and marked `blocked_on_human` in The Ledger at `architecture_and_roadmap.md:274`.
- The Ledger requires the chat route to always invoke `intercept_outbound_request` before provider streaming at `architecture_and_roadmap.md:292`.
- The Ledger says agents may scaffold, document, validate contracts, and add tests around checkpoints, but must not complete `TODO: Human Hands-On Implementation` blocks at `architecture_and_roadmap.md:257`.

## Open Areas

- No app-specific GitHub Actions workflow currently exists.
- Existing gateway tests do not directly cover provider adapter HTTP payloads, `_resolve_provider`, `_build_upstream_payload`, or stream relay cleanup behavior.
