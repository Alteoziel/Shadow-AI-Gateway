import logging
from contextlib import asynccontextmanager
from collections.abc import Awaitable, Callable
import time

from fastapi import FastAPI, Request, Response

from app.api.health import router as health_router
from app.api.v1.chat import router as chat_router
from app.config import get_settings
from app.proxy.correlation import (
    CORRELATION_ID_HEADER,
    parse_correlation_id,
    received_at_iso,
)

logger = logging.getLogger(__name__)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _configure_logging(settings.log_level)
    logging.getLogger(__name__).info(
        "Shadow AI Guardrail Gateway starting on %s:%s",
        settings.gateway_host,
        settings.gateway_port,
    )
    yield
    logging.getLogger(__name__).info("Shadow AI Guardrail Gateway shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Shadow AI Guardrail Gateway",
        description="Enterprise security proxy for outbound LLM traffic",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_logging_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = parse_correlation_id(request.headers)
        received_at = received_at_iso()
        request.state.correlation_id = correlation_id
        request.state.received_at = received_at

        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.exception(
                "request_failed method=%s path=%s elapsed_ms=%.2f "
                "correlation_id=%s received_at=%s",
                request.method,
                request.url.path,
                elapsed_ms,
                correlation_id,
                received_at,
            )
            raise

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        logger.info(
            "request_completed method=%s path=%s status_code=%s elapsed_ms=%.2f "
            "correlation_id=%s received_at=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            correlation_id,
            received_at,
        )
        return response

    app.include_router(health_router)
    app.include_router(chat_router)
    return app


app = create_app()
