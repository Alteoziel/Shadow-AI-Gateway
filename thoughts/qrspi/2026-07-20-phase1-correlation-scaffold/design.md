# Design Discussion

## Current State

- `create_app()` builds the FastAPI app and includes the health and chat routers; `/health` and `/v1/chat/completions` are both served through this app. See `research.md` Q1.
- The chat route awaits `intercept_outbound_request(...)` before resolving providers, building upstream payloads, or forwarding. See `research.md` Q2.
- The active checkpoint body in `app/proxy/interceptor.py` always raises `NotImplementedError`, and tests assert that contract remains true. See `research.md` Q2 and Q4.
- Logging is standard library logging configured in `app/main.py` lifespan, and chat currently logs only the checkpoint warning. See `research.md` Q3.
- No helper exists today for correlation IDs, received timestamps, or request lifecycle logging. See `research.md` Q3.

## Desired End State

The gateway should have observability scaffolding outside Human Checkpoint #1:

- A helper module can generate and parse correlation IDs from inbound headers.
- FastAPI middleware logs every request lifecycle, including `/health` and the current 501 chat path.
- Responses include the resolved correlation ID header so clients and logs can be connected.
- The chat route can pass correlation metadata around the interceptor call site without implementing the interceptor.
- `intercept_outbound_request` still raises `NotImplementedError`; contract tests still expect that.

## Autonomous Decisions

1. **Where should correlation helpers live?**
   - Options: put helpers in `app/main.py`, add `app/proxy/correlation.py`, or add a top-level observability package.
   - Chosen: `app/proxy/correlation.py`.
   - Rationale: The request metadata feeds the proxy path, but the project is small enough that a new top-level package would be premature.

2. **Which inbound header should be accepted?**
   - Options: accept only `X-Correlation-ID`, accept several aliases, or ignore inbound values.
   - Chosen: accept `X-Correlation-ID` and generate one when absent or invalid.
   - Rationale: A single conventional header keeps behavior obvious and testable without adding policy complexity.

3. **Should middleware add metadata to the interceptor body?**
   - Options: attach in the interceptor, attach in middleware state/headers, or inject into request body.
   - Chosen: store correlation metadata on `request.state` and response headers only.
   - Rationale: The task hard-stops attaching `correlation_id` / `received_at` inside `intercept_outbound_request`, and The Ledger forbids completing the human checkpoint.

4. **How should request logging be tested?**
   - Options: rely on manual log inspection, add `caplog` middleware tests, or add a new logging framework.
   - Chosen: add focused pytest `caplog` tests around `TestClient`.
   - Rationale: The repo already uses pytest, and standard logging is already configured.

5. **Should the interceptor cheat sheet be edited?**
   - Options: leave unchanged, add a pointer to helpers, or remove correlation wording.
   - Chosen: update comments only to point humans to the helper module and clarify not to implement in this change.
   - Rationale: The current cheat sheet mentions attaching correlation fields; a comment pointer reduces confusion while keeping the body unimplemented.

## Patterns to Follow

- Keep app assembly in `create_app()` so middleware covers all included routers (`research.md` Q1).
- Use standard library `logging.getLogger(__name__)`, matching `app/main.py` and `app/api/v1/chat.py` (`research.md` Q3).
- Preserve the chat route's order: interceptor first, provider resolution after (`research.md` Q2, Q4).
- Preserve `NotImplementedError` in the human checkpoint (`research.md` Q4).

## Design Decisions

1. **Correlation ID shape**: generated IDs use a short prefixed UUID value such as `corr_<32 hex chars>`; inbound IDs are accepted only when printable, stripped, and below a conservative length limit.
2. **Request lifecycle logging**: middleware logs one completion event with method, path, status code, elapsed milliseconds, correlation ID, and received timestamp.
3. **Failure logging**: middleware logs exceptions with the same correlation fields before re-raising so FastAPI behavior remains intact.
4. **Response propagation**: middleware writes `X-Correlation-ID` on successful/error responses returned by downstream handlers, including the current 501 chat response.
5. **Chat call-site logging**: the chat route logs before awaiting the interceptor and includes `correlation_id` from `request.state`; it does not add correlation fields to the interceptor body.

## What We're NOT Doing

- Not implementing `intercept_outbound_request`.
- Not attaching `correlation_id` or `received_at` inside the interceptor function body.
- Not adding database audit logs, metrics storage, tracing dependencies, or scrubbing logic.
- Not changing provider adapters or streaming behavior.
- Not changing the response body contract for `/health` or the 501 chat checkpoint path.

## Open Risks

- Log formatting is still text-based, so downstream log aggregation will parse key/value message fields rather than structured JSON.
- `request.state` metadata is process-local and intended only for in-request use, not persistence.
