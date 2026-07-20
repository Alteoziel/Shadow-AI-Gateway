from typing import Any

import httpx

from app.config import Settings
from app.proxy.providers.base import (
    BaseLLMProvider,
    map_httpx_error,
    require_api_key,
)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(BaseLLMProvider):
    """httpx-based OpenAI chat completions client."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.openai_api_key
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

    def _headers(self) -> dict[str, str]:
        api_key = require_api_key("openai", self._api_key)
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(
                OPENAI_CHAT_URL,
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise map_httpx_error("openai", exc) from exc

    async def chat_completion_stream(
        self,
        payload: dict[str, Any],
    ) -> httpx.Response:
        stream_payload = {**payload, "stream": True}
        response: httpx.Response | None = None
        try:
            response = await self._client.send(
                self._client.build_request(
                    "POST",
                    OPENAI_CHAT_URL,
                    headers=self._headers(),
                    json=stream_payload,
                ),
                stream=True,
            )
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            if response is not None:
                await response.aclose()
            raise map_httpx_error("openai", exc) from exc

    async def aclose(self) -> None:
        await self._client.aclose()
