from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    vector: list[float]
    input_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    thought_signature: str = ""


@dataclass(frozen=True, slots=True)
class ChatChunk:
    delta_text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


class AIProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_error",
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class BaseAIProvider(ABC):
    name: str

    @abstractmethod
    def generate_text(
        self,
        *,
        prompt: str,
        system_prompt: str = "",
        model_name: str | None = None,
        timeout: float,
        response_mime_type: str | None = None,
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> ProviderResponse:
        """Generate text through the configured provider."""

    @abstractmethod
    def generate_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str = "",
        model_name: str | None = None,
        timeout: float,
        temperature: float = 0.3,
        max_output_tokens: int = 1024,
    ) -> Iterator[ChatChunk]:
        """Stream a multi-turn chat completion with optional function calls."""

    @abstractmethod
    def embed_text(
        self,
        *,
        text: str,
        task_type: str,
        title: str = "",
        model_name: str | None = None,
        dimensions: int,
        timeout: float,
    ) -> EmbeddingResponse:
        """Create one embedding through the configured provider."""
