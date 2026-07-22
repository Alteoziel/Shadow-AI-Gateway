from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]]

    @field_validator("content")
    @classmethod
    def _bound_content(cls, value: str | list[dict[str, Any]]) -> str | list[dict[str, Any]]:
        if isinstance(value, str):
            if len(value) > 100_000:
                raise ValueError("message content exceeds 100000 characters")
            return value
        if len(value) > 200:
            raise ValueError("message content list exceeds 200 parts")
        return value


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request with optional provider override."""

    model: str = Field(..., min_length=1, max_length=128)
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=100)
    stream: bool = False
    provider: Literal["openai", "anthropic"] | None = None
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, ge=1, le=100_000)
    top_p: float | None = None
    stop: str | list[str] | None = None
    extra_body: dict[str, Any] = Field(default_factory=dict)

    @field_validator("extra_body")
    @classmethod
    def _bound_extra_body(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 50:
            raise ValueError("extra_body exceeds 50 keys")
        return value


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str | None = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str
    choices: list[ChatCompletionChoice]
    usage: dict[str, int] | None = None
