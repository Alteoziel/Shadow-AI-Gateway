import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import get_settings
from app.models.schemas import ChatCompletionRequest
from app.proxy.interceptor import intercept_outbound_request
from app.proxy.providers.anthropic import AnthropicProvider
from app.proxy.providers.base import BaseLLMProvider
from app.proxy.providers.openai import OpenAIProvider
from app.proxy.streaming import relay_sse_stream
from app.security.audit import AuditEventType, emit_audit
from app.security.auth import require_gateway_auth
from app.security.rate_limit import enforce_rate_limit

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

    for key, value in normalized.items():
        if key not in protected:
            payload[key] = value

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
    _auth_key: Annotated[str, Depends(require_gateway_auth)],
    _rate_key: Annotated[str, Depends(enforce_rate_limit)],
) -> JSONResponse | StreamingResponse:
    raw_body = request_body.model_dump(exclude_none=True)
    headers = {key: value for key, value in request.headers.items()}
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    key_id = getattr(request.state, "gateway_key_id", _auth_key)

    await emit_audit(
        AuditEventType.REQUEST_RECEIVED,
        correlation_id=correlation_id,
        user_id=key_id,
        model=request_body.model,
        metadata={"path": str(request.url.path), "stream": request_body.stream},
    )
    await emit_audit(
        AuditEventType.AUTH_OK,
        correlation_id=correlation_id,
        user_id=key_id,
    )

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
        await emit_audit(
            AuditEventType.INTERCEPTOR_BLOCK,
            correlation_id=correlation_id,
            user_id=key_id,
            blocked=True,
            reason="interceptor_not_implemented",
        )
        raise HTTPException(status_code=501, detail=CHECKPOINT_501_DETAIL) from exc
    except HTTPException as exc:
        await emit_audit(
            AuditEventType.INTERCEPTOR_BLOCK,
            correlation_id=correlation_id,
            user_id=key_id,
            blocked=True,
            reason=str(exc.detail),
            metadata={"status_code": exc.status_code},
        )
        raise

    await emit_audit(
        AuditEventType.INTERCEPTOR_OK,
        correlation_id=correlation_id,
        user_id=key_id,
        model=str(normalized.get("model", request_body.model)),
    )

    provider_name = _resolve_provider(request_body)
    provider = _get_provider_adapter(provider_name)
    payload = _build_upstream_payload(request_body, normalized)

    await emit_audit(
        AuditEventType.PROVIDER_CALL,
        correlation_id=correlation_id,
        user_id=key_id,
        provider=provider_name,
        model=str(payload.get("model")),
        metadata={"stream": request_body.stream},
    )

    if request_body.stream:
        try:
            upstream = await provider.chat_completion_stream(payload)
        except Exception as exc:
            await provider.aclose()
            await emit_audit(
                AuditEventType.PROVIDER_ERROR,
                correlation_id=correlation_id,
                user_id=key_id,
                provider=provider_name,
                blocked=True,
                reason=type(exc).__name__,
            )
            raise
        return await relay_sse_stream(upstream, on_complete=provider.aclose)

    try:
        result = await provider.chat_completion(payload)
        return JSONResponse(content=result)
    except Exception as exc:
        await emit_audit(
            AuditEventType.PROVIDER_ERROR,
            correlation_id=correlation_id,
            user_id=key_id,
            provider=provider_name,
            blocked=True,
            reason=type(exc).__name__,
        )
        raise
    finally:
        await provider.aclose()
