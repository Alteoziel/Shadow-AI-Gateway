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
    gateway_host: str = Field(default="0.0.0.0", alias="GATEWAY_HOST")  # noqa: S104
    gateway_port: int = Field(default=8000, alias="GATEWAY_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    # Comma-separated alternate keys; GATEWAY_API_KEY is the primary.
    gateway_api_key: str = Field(default="", alias="GATEWAY_API_KEY")
    gateway_api_keys: str = Field(default="", alias="GATEWAY_API_KEYS")
    gateway_rate_limit_per_minute: int = Field(
        default=60,
        alias="GATEWAY_RATE_LIMIT_PER_MINUTE",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Test helper — reload settings after env changes."""
    get_settings.cache_clear()
