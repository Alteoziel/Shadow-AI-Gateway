from abc import ABC, abstractmethod
from typing import Any

import httpx


class BaseLLMProvider(ABC):
    """Abstract async interface for upstream LLM chat completion."""

    @abstractmethod
    async def chat_completion(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Non-streaming chat completion."""

    @abstractmethod
    async def chat_completion_stream(
        self,
        payload: dict[str, Any],
    ) -> httpx.Response:
        """Return an open streaming httpx response (caller closes/relays)."""

    @abstractmethod
    async def aclose(self) -> None:
        """Release underlying HTTP client resources."""
