from collections.abc import Mapping
from typing import Any


async def intercept_outbound_request(
    *,
    body: dict[str, Any],
    headers: Mapping[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Pre-flight choke point: validate and normalize outbound LLM payloads
    before any provider adapter is invoked.

    Human Checkpoint #1 — see architecture_and_roadmap.md §6.
    """
    # -------------------------------------------------------------------------
    # TODO: Human Hands-On Implementation
    #
    # Implement pre-flight validation and normalization here. The chat route
    # calls this function before every upstream provider request.
    #
    # Cheat sheet (why this works):
    # 1. Pre-flight means inspect/normalize the outbound payload **before** any
    #    bytes hit OpenAI/Anthropic — this is the choke point for later scrubbing
    #    and audit.
    # 2. `async def` keeps the event loop free to serve other requests while
    #    awaiting I/O; the gateway must not block on a single upstream call.
    # 3. Return a normalized internal request that provider adapters can stream
    #    against; raise HTTPException(4xx) on invalid input and never call
    #    providers on bad payloads.
    #
    # Scope: validate required fields (model, messages), attach correlation_id /
    # received_at, return upstream-ready payload. The surrounding request
    # lifecycle helper lives in app/proxy/correlation.py; do not duplicate ID
    # generation policy here. Do NOT implement scrubbing (Phase 2) or DB
    # inserts (Phase 3).
    # -------------------------------------------------------------------------
    raise NotImplementedError(
        "Checkpoint #1 pending: implement intercept_outbound_request in "
        "app/proxy/interceptor.py (see architecture_and_roadmap.md §6)."
    )
