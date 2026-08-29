"""Provider-neutral AI generation boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable


class AIProviderError(RuntimeError):
    """Normalized provider failure that never contains credentials or payloads."""


class AIProviderUnavailable(AIProviderError):
    """The provider timed out or returned a retryable service failure."""


class AIProviderRejected(AIProviderError):
    """The provider rejected a valid bounded generation request."""


@dataclass(frozen=True, slots=True)
class AIMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class AIGenerationRequest:
    messages: tuple[AIMessage, ...]
    max_output_tokens: int
    temperature: float = 0.1


@dataclass(frozen=True, slots=True)
class AIProviderResponse:
    content: str
    model: str
    provider_request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


@runtime_checkable
class AIProviderClient(Protocol):
    async def generate(self, request: AIGenerationRequest) -> AIProviderResponse: ...

    async def health_check(self) -> bool: ...

    async def close(self) -> None: ...
