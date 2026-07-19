import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.chat import router as chat_router
from app.config import get_settings


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
    app.include_router(health_router)
    app.include_router(chat_router)
    return app


app = create_app()
