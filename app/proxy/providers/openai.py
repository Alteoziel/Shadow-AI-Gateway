from typing import Any

import httpx

from app.config import Settings
from app.proxy.providers.base import BaseLLMProvider
from app.security.egress import assert_allowed_url
from app.security.http import EgressCheckedAsyncClient

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(BaseLLMProvider):
    """httpx-based OpenAI chat completions client."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.openai_api_key
        self._client = EgressCheckedAsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
        assert_allowed_url(OPENAI_CHAT_URL)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        assert_allowed_url(OPENAI_CHAT_URL)
        response = await self._client.post(
            OPENAI_CHAT_URL,
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def chat_completion_stream(
        self,
        payload: dict[str, Any],
    ) -> httpx.Response:
        assert_allowed_url(OPENAI_CHAT_URL)
        stream_payload = {**payload, "stream": True}
        return await self._client.send(
            self._client.build_request(
                "POST",
                OPENAI_CHAT_URL,
                headers=self._headers(),
                json=stream_payload,
            ),
            stream=True,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
