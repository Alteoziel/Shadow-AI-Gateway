from collections.abc import Mapping
from typing import Any
from fastapi import HTTPException
from datetime import UTC, datetime
from uuid import uuid4


async def intercept_outbound_request(
    *,
    body: dict[str, Any],
    headers: Mapping[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:

    model = body.get("model")
    messages = body.get("messages")
    if not isinstance(model, str) or not model.strip():
        raise HTTPException(status_code=400, detail="model is required")
    if not isinstance(messages, list) or len(messages) < 1:
        raise HTTPException(status_code=400, detail="messages must be a non-empty list")
    for message in messages:
        if not isinstance(message, dict) or "role" not in message or "content" not in message:
            raise HTTPException(status_code=400, detail="each message needs role and content")
    correlation_id = str(uuid4())
    received_at = datetime.now(UTC).isoformat()
    normalized = body.copy()
    normalized["correlation_id"] = correlation_id
    normalized["received_at"] = received_at
    return normalized
