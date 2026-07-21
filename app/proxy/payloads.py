from __future__ import annotations

from collections.abc import Mapping
from typing import Any

FUZZ_TARGETS = ("to_anthropic_payload",)


def to_anthropic_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map OpenAI-compatible gateway payload to Anthropic Messages API."""
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")

    model = payload.get("model")
    if not isinstance(model, str) or not model:
        raise ValueError("payload must include a non-empty model")

    raw_messages = payload.get("messages", [])
    if not isinstance(raw_messages, list):
        raise ValueError("payload messages must be a list")

    messages = []
    system_parts: list[str] = []

    for message in raw_messages:
        if not isinstance(message, Mapping):
            continue

        role = message.get("role")
        content = message.get("content", "")
        if role == "system":
            if isinstance(content, str):
                system_parts.append(content)
            else:
                system_parts.append(str(content))
            continue
        if role == "user":
            messages.append({"role": "user", "content": content})
            continue
        if role == "assistant":
            messages.append({"role": "assistant", "content": content})
            continue
        # tool / function / unknown roles are not 1:1 on Anthropic Messages
        # without tool_use blocks — skip rather than mislabel as assistant
        continue

    anthropic_payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": payload.get("max_tokens", 1024),
    }
    if system_parts:
        anthropic_payload["system"] = "\n\n".join(system_parts)
    if payload.get("temperature") is not None:
        anthropic_payload["temperature"] = payload["temperature"]
    if payload.get("top_p") is not None:
        anthropic_payload["top_p"] = payload["top_p"]
    if payload.get("stop") is not None:
        anthropic_payload["stop_sequences"] = (
            [payload["stop"]] if isinstance(payload["stop"], str) else payload["stop"]
        )
    return anthropic_payload
