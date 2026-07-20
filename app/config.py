from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Phase 1 configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    default_provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        alias="DEFAULT_PROVIDER",
    )
    gateway_host: str = Field(default="0.0.0.0", alias="GATEWAY_HOST")
    gateway_port: int = Field(default=8000, alias="GATEWAY_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
