from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException

from app.proxy.correlation import parse_correlation_id, received_at_iso


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
    model = body.get("model")
    messages = body.get("messages")
    if not isinstance(model, str) or not model.strip():
        raise HTTPException(status_code=400, detail="model is required")
    if not isinstance(messages, list) or len(messages) < 1:
        raise HTTPException(status_code=400, detail="messages must be a non-empty list")
    for message in messages:
        if (
            not isinstance(message, dict)
            or "role" not in message
            or "content" not in message
        ):
            raise HTTPException(
                status_code=400,
                detail="each message needs role and content",
            )

    normalized = body.copy()
    normalized["model"] = model
    normalized["messages"] = messages
    # Reuse correlation helpers — do not invent a parallel ID policy.
    normalized["correlation_id"] = parse_correlation_id(headers)
    normalized["received_at"] = received_at_iso()
    return normalized
