from typing import Any

import httpx

from app.config import Settings
from app.proxy.payloads import to_anthropic_payload
from app.proxy.providers.base import BaseLLMProvider

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(BaseLLMProvider):
    """httpx-based Anthropic Messages API client (OpenAI-shaped gateway payload)."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.anthropic_api_key
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        anthropic_payload = to_anthropic_payload(payload)
        response = await self._client.post(
            ANTHROPIC_MESSAGES_URL,
            headers=self._headers(),
            json=anthropic_payload,
        )
        response.raise_for_status()
        data = response.json()
        return self._to_openai_shape(data, model=payload["model"])

    async def chat_completion_stream(
        self,
        payload: dict[str, Any],
    ) -> httpx.Response:
        anthropic_payload = {
            **to_anthropic_payload(payload),
            "stream": True,
        }
        return await self._client.send(
            self._client.build_request(
                "POST",
                ANTHROPIC_MESSAGES_URL,
                headers=self._headers(),
                json=anthropic_payload,
            ),
            stream=True,
        )

    @staticmethod
    def _to_openai_shape(data: dict[str, Any], *, model: str) -> dict[str, Any]:
        """Convert Anthropic message response to OpenAI-compatible chat completion."""
        text_blocks = [
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        return {
            "id": data.get("id", "anthropic-msg"),
            "object": "chat.completion",
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "".join(text_blocks)},
                    "finish_reason": data.get("stop_reason"),
                }
            ],
            "usage": {
                "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                "total_tokens": (
                    data.get("usage", {}).get("input_tokens", 0)
                    + data.get("usage", {}).get("output_tokens", 0)
                ),
            },
        }

    async def aclose(self) -> None:
        await self._client.aclose()
