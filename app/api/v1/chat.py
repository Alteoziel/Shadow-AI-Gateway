import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import get_settings
from app.models.schemas import ChatCompletionRequest
from app.proxy.interceptor import intercept_outbound_request
from app.proxy.providers.anthropic import AnthropicProvider
from app.proxy.providers.base import BaseLLMProvider
from app.proxy.providers.openai import OpenAIProvider
from app.proxy.streaming import relay_sse_stream

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])

CHECKPOINT_501_DETAIL = (
    "Checkpoint #1 pending: intercept_outbound_request is not yet implemented. "
    "A human must complete app/proxy/interceptor.py before provider forwarding "
    "can proceed (see architecture_and_roadmap.md §6)."
)


def _resolve_provider(request: ChatCompletionRequest) -> str:
    settings = get_settings()
    return request.provider or settings.default_provider


def _get_provider_adapter(provider_name: str) -> BaseLLMProvider:
    settings = get_settings()
    if provider_name == "openai":
        return OpenAIProvider(settings)
    if provider_name == "anthropic":
        return AnthropicProvider(settings)
    raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider_name}")


def _build_upstream_payload(
    request: ChatCompletionRequest,
    normalized: dict[str, Any],
) -> dict[str, Any]:
    """Merge normalized interceptor output with gateway request fields.

    Interceptor-normalized `model` / `messages` / `stream` always win.
    `extra_body` may only supply additive keys that do not override those.
    """
    protected = {"model", "messages", "stream"}
    payload: dict[str, Any] = {}

    # Additive extras first (cannot win over protected fields later)
    if request.extra_body:
        for key, value in request.extra_body.items():
            if key not in protected:
                payload[key] = value

    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens
    if request.top_p is not None:
        payload["top_p"] = request.top_p
    if request.stop is not None:
        payload["stop"] = request.stop

    # Non-protected normalized metadata
    for key, value in normalized.items():
        if key not in protected:
            payload[key] = value

    # Protected fields last — interceptor + request contract enforce these
    payload["model"] = normalized.get("model", request.model)
    payload["messages"] = normalized.get(
        "messages", [m.model_dump() for m in request.messages]
    )
    payload["stream"] = request.stream
    return payload


@router.post("/chat/completions", response_model=None)
async def chat_completions(
    request_body: ChatCompletionRequest,
    request: Request,
) -> JSONResponse | StreamingResponse:
    raw_body = request_body.model_dump(exclude_none=True)
    headers = {key: value for key, value in request.headers.items()}
    correlation_id = getattr(request.state, "correlation_id", None)

    try:
        logger.info(
            "interceptor_invoked path=%s correlation_id=%s",
            request.url.path,
            correlation_id,
        )
        normalized = await intercept_outbound_request(
            body=raw_body,
            headers=headers,
            metadata={"path": str(request.url.path)},
        )
    except NotImplementedError as exc:
        logger.warning(
            "Interceptor checkpoint not implemented correlation_id=%s: %s",
            correlation_id,
            exc,
        )
        raise HTTPException(status_code=501, detail=CHECKPOINT_501_DETAIL) from exc

    provider_name = _resolve_provider(request_body)
    provider = _get_provider_adapter(provider_name)
    payload = _build_upstream_payload(request_body, normalized)

    if request_body.stream:
        # Hand off aclose to the stream consumer. If setup fails before that,
        # close here so the httpx client does not leak.
        try:
            upstream = await provider.chat_completion_stream(payload)
        except Exception:
            await provider.aclose()
            raise
        return await relay_sse_stream(upstream, on_complete=provider.aclose)

    try:
        result = await provider.chat_completion(payload)
        return JSONResponse(content=result)
    finally:
        await provider.aclose()
