# Research Findings

## Q1: How does `POST /v1/chat/completions` flow from request validation through interceptor invocation, provider selection, and streaming or non-streaming response generation?

### Findings
- The FastAPI app includes the chat router from `app.api.v1.chat` during app creation (`app/main.py:30-39`).
- `ChatCompletionRequest` validates `model`, `messages`, `stream`, optional `provider`, sampling fields, `stop`, and `extra_body` before the route body runs (`app/models/schemas.py:11-23`).
- `chat_completions` builds `raw_body` from the validated request and copies inbound headers before invoking `intercept_outbound_request` (`app/api/v1/chat.py:80-94`).
- The route catches `NotImplementedError` from the interceptor, logs it, and raises HTTP 501 with the `CHECKPOINT_501_DETAIL` message (`app/api/v1/chat.py:18-23`, `app/api/v1/chat.py:88-97`).
- Provider selection happens after the interceptor call. `_resolve_provider` uses the request provider override or `settings.default_provider`; `_get_provider_adapter` instantiates OpenAI or Anthropic adapters and raises HTTP 400 for unknown names (`app/api/v1/chat.py:26-37`, `app/api/v1/chat.py:99-100`).
- `_build_upstream_payload` prevents `extra_body` from overriding `model`, `messages`, or `stream`, copies optional sampling fields, adds non-protected normalized metadata, then sets protected fields last (`app/api/v1/chat.py:40-78`).
- Streaming requests call `provider.chat_completion_stream(payload)`, close the provider if setup fails, and return `relay_sse_stream(upstream, on_complete=provider.aclose)` (`app/api/v1/chat.py:103-111`).
- Non-streaming requests call `provider.chat_completion(payload)`, wrap the returned dict in `JSONResponse`, and close the provider in `finally` (`app/api/v1/chat.py:113-117`).

## Q2: How do the OpenAI and Anthropic provider adapters currently build upstream requests, consume `httpx` responses, and surface errors?

### Findings
- `BaseLLMProvider` defines async `chat_completion`, `chat_completion_stream`, and `aclose`; streaming returns an open `httpx.Response` for the caller to relay and close (`app/proxy/providers/base.py:7-26`).
- `OpenAIProvider` stores `settings.openai_api_key`, creates an `httpx.AsyncClient` with a 120s total timeout and 10s connect timeout, and sends `Authorization: Bearer <key>` plus JSON content headers (`app/proxy/providers/openai.py:12-22`).
- OpenAI non-streaming posts directly to `https://api.openai.com/v1/chat/completions`, calls `response.raise_for_status()`, and returns `response.json()` (`app/proxy/providers/openai.py:24-31`).
- OpenAI streaming forces `"stream": True`, builds the POST request, and sends it with `stream=True`; it does not call `raise_for_status()` before returning the response (`app/proxy/providers/openai.py:33-46`).
- `AnthropicProvider` stores `settings.anthropic_api_key`, creates the same timeout-shaped `httpx.AsyncClient`, and sends `x-api-key`, `anthropic-version`, and JSON content headers (`app/proxy/providers/anthropic.py:12-24`).
- Anthropic maps OpenAI-shaped messages into the Messages API shape, moving `system` role content into a joined `system` string, preserving `user` and `assistant`, skipping roles without a 1:1 mapping, defaulting `max_tokens` to 1024, and mapping `stop` to `stop_sequences` (`app/proxy/providers/anthropic.py:27-68`).
- Anthropic non-streaming posts to `https://api.anthropic.com/v1/messages`, calls `response.raise_for_status()`, parses JSON, and converts the message response into OpenAI-compatible chat-completion JSON (`app/proxy/providers/anthropic.py:70-79`, `app/proxy/providers/anthropic.py:100-126`).
- Anthropic streaming maps the payload, adds `"stream": True`, builds the Messages request, and sends it with `stream=True`; it returns the raw `httpx.Response` without status normalization (`app/proxy/providers/anthropic.py:81-97`).
- No provider module catches `httpx.HTTPStatusError`, timeout exceptions, request errors, or JSON parsing failures; existing `raise_for_status()` exceptions propagate out of non-streaming adapters (`app/proxy/providers/openai.py:24-31`, `app/proxy/providers/anthropic.py:70-79`).

## Q3: What configuration patterns exist for provider API keys and default provider selection, including validation behavior for missing or empty environment values?

### Findings
- `Settings` is a `pydantic_settings.BaseSettings` class with `.env` loading, UTF-8 encoding, and `extra="ignore"` (`app/config.py:7-15`).
- `openai_api_key` and `anthropic_api_key` default to empty strings and map to `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` aliases (`app/config.py:17-18`).
- `default_provider` is a `Literal["openai", "anthropic"]`, defaults to `"openai"`, and maps to `DEFAULT_PROVIDER` (`app/config.py:19-22`).
- `get_settings()` is `lru_cache`-cached and returns a `Settings` instance (`app/config.py:28-30`).
- Provider constructors read the relevant key directly from settings and construct headers immediately when requests are made; there is no key validation in `Settings`, route provider resolution, or provider constructors (`app/config.py:17-18`, `app/proxy/providers/openai.py:14-22`, `app/proxy/providers/anthropic.py:14-24`).

## Q4: How is streaming currently represented by the gateway, especially for OpenAI-compatible chunks and Anthropic chunks?

### Findings
- `relay_sse_stream` accepts an upstream `httpx.Response`, iterates `upstream.aiter_bytes()`, yields chunks unchanged, then closes the upstream and calls optional `on_complete` (`app/proxy/streaming.py:7-27`).
- The returned `StreamingResponse` uses the upstream status code, `text/event-stream` media type by default, and forwards upstream headers except `content-length`, `transfer-encoding`, and `connection` (`app/proxy/streaming.py:29-38`).
- `iter_sse_lines` exists and yields decoded upstream lines via `upstream.aiter_lines()`, but no current route or provider uses it (`app/proxy/streaming.py:41-43`; `app/api/v1/chat.py:103-111`).
- OpenAI streaming returns OpenAI's upstream SSE bytes directly through `relay_sse_stream` (`app/proxy/providers/openai.py:33-46`, `app/api/v1/chat.py:103-111`).
- Anthropic streaming returns Anthropic Messages API SSE bytes directly through the same relay path; unlike non-streaming Anthropic responses, streaming chunks are not converted to OpenAI-compatible chunk shape (`app/proxy/providers/anthropic.py:81-97`, `app/proxy/streaming.py:20-38`).

## Q5: What test coverage already exists for provider routing, streaming, error paths, and the human-owned interceptor contract?

### Findings
- `test_chat_returns_501_while_interceptor_not_implemented` posts a valid chat payload and asserts HTTP 501 plus detail text containing `Checkpoint #1` and `intercept_outbound_request` (`tests/test_proxy_routing.py:16-22`).
- `test_chat_forwards_to_provider_after_interceptor_implemented` patches the interceptor to return a normalized payload, patches `OpenAIProvider`, posts a non-streaming payload, and asserts HTTP 200, provider delegation, and provider close (`tests/test_proxy_routing.py:25-64`).
- `test_intercept_outbound_request_exists_and_is_async` asserts the interceptor is callable and coroutine-based (`tests/test_interceptor_contract.py:10-13`).
- `test_intercept_outbound_request_raises_not_implemented` calls the interceptor directly and asserts it raises `NotImplementedError` containing `Checkpoint #1` (`tests/test_interceptor_contract.py:16-19`).
- `test_chat_route_calls_interceptor_before_provider` parses `app/api/v1/chat.py` AST/source and asserts `intercept_outbound_request` appears before provider-related hints in source order (`tests/test_interceptor_contract.py:22-45`).
- The visible test suite does not include provider adapter unit tests, upstream `httpx` exception mapping tests, missing API key tests, or streaming shape tests for either provider (`tests/test_proxy_routing.py`, `tests/test_interceptor_contract.py`, `tests/test_health.py`).

## Cross-Cutting Observations
- The route is the only current layer translating the human checkpoint `NotImplementedError` into a gateway HTTP error (`app/api/v1/chat.py:88-97`).
- Provider adapters own upstream URL/header/payload details and client lifetime, while the route owns provider selection and response type selection (`app/api/v1/chat.py:26-37`, `app/proxy/providers/openai.py:12-49`, `app/proxy/providers/anthropic.py:12-129`).
- Non-streaming Anthropic responses are OpenAI-shaped, while Anthropic streaming responses are raw Anthropic SSE chunks (`app/proxy/providers/anthropic.py:70-79`, `app/proxy/providers/anthropic.py:81-97`, `app/proxy/streaming.py:20-38`).
- The existing tests intentionally keep Checkpoint #1 blocked while still documenting how provider routing works once the interceptor is patched in tests (`tests/test_proxy_routing.py:16-64`, `tests/test_interceptor_contract.py:16-45`).

## Open Areas
- No current test fixtures demonstrate `httpx.Response` streaming behavior in the provider layer.
- No current docs explicitly state whether Anthropic streaming raw relay is intentional or temporary.
