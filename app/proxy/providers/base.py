from abc import ABC, abstractmethod
from typing import Any

import httpx
from fastapi import HTTPException


def require_api_key(provider_name: str, api_key: str) -> str:
    """Return a configured provider key or raise a clear gateway error."""
    stripped = api_key.strip()
    if stripped:
        return stripped

    raise HTTPException(
        status_code=500,
        detail={
            "error": "provider_configuration_error",
            "provider": provider_name,
            "message": f"{provider_name} API key is not configured",
        },
    )


def map_httpx_error(provider_name: str, exc: httpx.HTTPError) -> HTTPException:
    """Convert upstream httpx failures into stable gateway HTTP errors."""
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return HTTPException(
            status_code=502,
            detail={
                "error": "upstream_http_error",
                "provider": provider_name,
                "upstream_status_code": status_code,
                "message": f"{provider_name} upstream returned HTTP {status_code}",
            },
        )

    if isinstance(exc, httpx.TimeoutException):
        return HTTPException(
            status_code=504,
            detail={
                "error": "upstream_timeout",
                "provider": provider_name,
                "message": f"{provider_name} upstream request timed out",
            },
        )

    if isinstance(exc, httpx.RequestError):
        return HTTPException(
            status_code=502,
            detail={
                "error": "upstream_request_error",
                "provider": provider_name,
                "message": f"{provider_name} upstream request failed",
            },
        )

    return HTTPException(
        status_code=502,
        detail={
            "error": "upstream_error",
            "provider": provider_name,
            "message": f"{provider_name} upstream request failed",
        },
    )


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
