"""Production adapter for providers implementing the OpenAI chat-completions API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from packages.python.clients.ai import (
    AIGenerationRequest,
    AIProviderRejected,
    AIProviderResponse,
    AIProviderUnavailable,
)


class OpenAICompatibleAIProviderClient:
    """Bounded HTTP adapter with normalized errors and no payload logging."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 15.0,
        max_retries: int = 1,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._model = model
        self._max_retries = max(0, min(max_retries, 2))
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 5.0)),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            follow_redirects=False,
        )

    async def generate(self, request: AIGenerationRequest) -> AIProviderResponse:
        payload = {
            "model": self._model,
            "messages": [
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            "max_tokens": request.max_output_tokens,
            "temperature": request.temperature,
        }
        response: httpx.Response | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post("chat/completions", json=payload)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= self._max_retries:
                    raise AIProviderUnavailable("The AI provider is unavailable") from exc
                await asyncio.sleep(0.2 * (2**attempt))
                continue
            if response.status_code in {408, 429} or response.status_code >= 500:
                if attempt < self._max_retries:
                    await asyncio.sleep(0.2 * (2**attempt))
                    continue
                raise AIProviderUnavailable("The AI provider is unavailable")
            if response.status_code >= 400:
                raise AIProviderRejected("The AI provider rejected the request")
            break

        if response is None:  # defensive; all loop paths either set response or raise
            raise AIProviderUnavailable("The AI provider is unavailable")
        try:
            data: dict[str, Any] = response.json()
            content = str(data["choices"][0]["message"]["content"]).strip()
            usage = data.get("usage") or {}
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderUnavailable("The AI provider returned an invalid response") from exc
        if not content:
            raise AIProviderUnavailable("The AI provider returned an empty response")
        return AIProviderResponse(
            content=content,
            model=str(data.get("model") or self._model),
            provider_request_id=response.headers.get("x-request-id"),
            input_tokens=_optional_int(usage.get("prompt_tokens")),
            output_tokens=_optional_int(usage.get("completion_tokens")),
        )

    async def health_check(self) -> bool:
        try:
            response = await self._client.get("models")
        except (httpx.TimeoutException, httpx.NetworkError):
            return False
        return response.is_success

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None
