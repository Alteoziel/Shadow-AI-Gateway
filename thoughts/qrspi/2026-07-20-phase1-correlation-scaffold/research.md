# Research Findings

## Q1: How is the FastAPI application assembled, and how do requests reach `/health` and `/v1/chat/completions`?

### Findings

- `app/main.py` defines `_configure_logging`, `lifespan`, `create_app`, and module-level `app`; `create_app()` constructs `FastAPI` with title, description, version, and lifespan, then includes the health and chat routers.
- `app/api/health.py` defines an `APIRouter` tagged `health`; `@router.get("/health")` returns `{"status": "ok"}`.
- `app/api/v1/chat.py` defines an `APIRouter(prefix="/v1", tags=["chat"])`; `@router.post("/chat/completions")` exposes `/v1/chat/completions`.

## Q2: What is the current proxy call flow from the chat endpoint through the interceptor and provider streaming helpers?

### Findings

- `chat_completions()` receives `ChatCompletionRequest` and `Request`, dumps the Pydantic body with `exclude_none=True`, copies request headers, and awaits `intercept_outbound_request(body=..., headers=..., metadata={"path": ...})`.
- If `intercept_outbound_request` raises `NotImplementedError`, the chat route logs a warning and raises `HTTPException(status_code=501, detail=CHECKPOINT_501_DETAIL)`.
- After the interceptor returns, `_resolve_provider()` chooses the request provider or default settings provider; `_get_provider_adapter()` creates an OpenAI or Anthropic adapter or raises 400 for unsupported providers.
- `_build_upstream_payload()` merges additive `extra_body`, optional sampling fields, normalized metadata, and protected `model` / `messages` / `stream` fields.
- Non-streaming calls await `provider.chat_completion(payload)`, return a `JSONResponse`, and close the provider in `finally`.
- Streaming calls await `provider.chat_completion_stream(payload)` and pass the open response to `relay_sse_stream(..., on_complete=provider.aclose)`.
- `relay_sse_stream()` yields upstream bytes from `httpx.Response.aiter_bytes()`, then closes both the upstream response and optional provider completion callback in a `finally` block.
- `app/proxy/interceptor.py` currently contains the Human Checkpoint #1 TODO and always raises `NotImplementedError`.

## Q3: What logging, request metadata, or observability patterns already exist in the gateway code?

### Findings

- `app/main.py` configures standard library logging in the FastAPI lifespan using `settings.log_level`, with format `%(asctime)s %(levelname)s [%(name)s] %(message)s`.
- The application logs gateway startup and shutdown with host/port through `logging.getLogger(__name__)`.
- `app/api/v1/chat.py` uses a module logger and currently logs only the interceptor checkpoint warning path.
- Existing request metadata passed into the interceptor contains only `{"path": str(request.url.path)}`.
- No existing helper module for correlation IDs, received timestamps, request IDs, or access logging was found under `app/`.

## Q4: What do the existing tests assert for health, proxy routing, and the interceptor contract?

### Findings

- `tests/test_health.py` creates `TestClient(app)`, calls `GET /health`, and asserts status 200 with body `{"status": "ok"}`.
- `tests/test_proxy_routing.py` asserts `POST /v1/chat/completions` returns 501 while the interceptor is unimplemented and that the response detail mentions `Checkpoint #1` and `intercept_outbound_request`.
- `tests/test_proxy_routing.py` also documents the unlock path by monkeypatching `app.api.v1.chat.intercept_outbound_request` to return normalized data and `OpenAIProvider` to an async mock, then asserting a 200 response and provider close.
- `tests/test_interceptor_contract.py` asserts `intercept_outbound_request` is callable, async, and raises `NotImplementedError` containing `Checkpoint #1`.
- `tests/test_interceptor_contract.py` parses `app/api/v1/chat.py` with `ast` and asserts an `intercept_outbound_request` call exists before the first provider-related source hint.

## Q5: What project commands and dependency conventions are used to run gateway tests?

### Findings

- Root `pyproject.toml` declares Python `>=3.12`, runtime dependencies `fastapi`, `uvicorn[standard]`, `httpx`, and `pydantic-settings`.
- Root `pyproject.toml` declares dev dependencies `pytest`, `pytest-asyncio`, and `httpx`.
- Root `pyproject.toml` configures pytest with `asyncio_mode = "auto"` and `testpaths = ["tests"]`, so `pytest` from the repository root runs gateway tests.

## Cross-Cutting Observations

- The active request path already guarantees the interceptor is called before provider creation or forwarding.
- Tests intentionally treat the unimplemented interceptor as the current contract while still documenting the future provider path via monkeypatching.
- Logging uses Python's standard library rather than a structured logging dependency.

## Open Areas

- The codebase does not currently define a correlation ID format or inbound header convention.
- No explicit log capture tests exist yet for request lifecycle logging.
