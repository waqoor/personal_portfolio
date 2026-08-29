from __future__ import annotations

import httpx
import pytest
from pydantic import ValidationError

from packages.python.clients.ai import AIGenerationRequest, AIMessage, AIProviderRejected
from packages.python.clients.github_repository import GitHubRepositoryMetadataClient
from packages.python.clients.openai_compatible_ai import OpenAICompatibleAIProviderClient
from packages.python.clients.repository_metadata import RepositoryMetadataProviderError
from packages.python.clients.smtp_email import SMTPEmailClient
from packages.python.common.settings import Settings


@pytest.mark.asyncio
async def test_ai_adapter_normalizes_response_and_bounds_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.headers["authorization"] == "Bearer provider-secret"
        if calls == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            request=request,
            headers={"x-request-id": "provider-request"},
            json={
                "model": "provider-model",
                "choices": [{"message": {"content": "Grounded answer [S1]."}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 8},
            },
        )

    http_client = httpx.AsyncClient(
        base_url="https://provider.example/v1/",
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer provider-secret"},
    )
    adapter = OpenAICompatibleAIProviderClient(
        base_url="https://provider.example/v1/",
        api_key="provider-secret",
        model="configured-model",
        max_retries=1,
        client=http_client,
    )
    try:
        response = await adapter.generate(
            AIGenerationRequest(
                messages=(AIMessage(role="user", content="Question"),),
                max_output_tokens=100,
            )
        )
    finally:
        await http_client.aclose()

    assert calls == 2
    assert response.content == "Grounded answer [S1]."
    assert response.provider_request_id == "provider-request"
    assert response.input_tokens == 20


@pytest.mark.asyncio
async def test_ai_adapter_does_not_leak_provider_rejection_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            request=request,
            text="sensitive provider diagnostic and echoed prompt",
        )

    http_client = httpx.AsyncClient(
        base_url="https://provider.example/v1/",
        transport=httpx.MockTransport(handler),
    )
    adapter = OpenAICompatibleAIProviderClient(
        base_url="https://provider.example/v1/",
        api_key="secret",
        model="model",
        client=http_client,
    )
    try:
        with pytest.raises(AIProviderRejected) as caught:
            await adapter.generate(
                AIGenerationRequest(
                    messages=(AIMessage(role="user", content="private question"),),
                    max_output_tokens=100,
                )
            )
    finally:
        await http_client.aclose()

    assert "sensitive" not in str(caught.value)
    assert "private question" not in str(caught.value)


@pytest.mark.asyncio
async def test_github_repository_adapter_normalizes_etag_rate_and_privacy_states() -> None:
    responses = [
        httpx.Response(
            200,
            headers={"ETag": '"repo-v1"'},
            json={
                "full_name": "owner/repository",
                "language": "Python",
                "stargazers_count": 12,
                "forks_count": 3,
                "private": False,
            },
        ),
        httpx.Response(304),
        httpx.Response(429, headers={"Retry-After": "120"}),
        httpx.Response(404, text="private provider details must not leak"),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        response = responses.pop(0)
        response.request = request
        return response

    http_client = httpx.AsyncClient(
        base_url="https://api.github.com",
        transport=httpx.MockTransport(handler),
    )
    adapter = GitHubRepositoryMetadataClient(client=http_client)
    try:
        result = await adapter.fetch("https://github.com/owner/repository.git")
        assert (result.repository_identity, result.stars, result.forks) == (
            "owner/repository",
            12,
            3,
        )
        unchanged = await adapter.fetch("https://github.com/owner/repository", etag='"repo-v1"')
        assert unchanged.not_modified is True
        with pytest.raises(RepositoryMetadataProviderError) as rate_limited:
            await adapter.fetch("https://github.com/owner/repository")
        assert rate_limited.value.code == "rate_limited"
        assert rate_limited.value.retry_after_seconds == 120
        with pytest.raises(RepositoryMetadataProviderError) as unavailable:
            await adapter.fetch("https://github.com/owner/repository")
        assert unavailable.value.code == "not_found_or_private"
        assert "private provider details" not in str(unavailable.value)
        with pytest.raises(RepositoryMetadataProviderError):
            await adapter.fetch("https://evil.example/owner/repository")
    finally:
        await http_client.aclose()


def test_smtp_adapter_rejects_header_injection() -> None:
    with pytest.raises(ValueError):
        SMTPEmailClient(
            host="smtp.example.com",
            port=587,
            from_address="sender@example.com\r\nBcc: attacker@example.com",
            contact_recipient="owner@example.com",
        )


def _production_settings(**changes: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "environment": "production",
        "database_url": "postgresql+asyncpg://portfolio:unique-db-secret-2026@db:5432/portfolio",
        "auth_secret": "unique-auth-secret-with-at-least-32-random-characters",
        "privacy_hash_secret": "unique-privacy-secret-with-at-least-32-random-characters",
        "cookie_secure": True,
        "public_base_url": "https://portfolio.example",
        "api_public_url": "https://portfolio.example/api",
        "allowed_origins": ["https://portfolio.example"],
        "allowed_hosts": ["portfolio.example", "api"],
        "docs_enabled": False,
    }
    values.update(changes)
    return Settings(**values)  # type: ignore[arg-type]


def test_production_settings_fail_closed_for_placeholder_secrets() -> None:
    with pytest.raises(ValidationError):
        _production_settings(privacy_hash_secret="CHANGE_ME_WITH_32_CHARACTERS_OR_MORE")


def test_production_settings_require_configured_ai_when_enabled() -> None:
    with pytest.raises(ValidationError):
        _production_settings(assistant_enabled=True)


def test_production_settings_accept_complete_secure_configuration() -> None:
    settings = _production_settings()
    assert settings.environment == "production"
    assert settings.public_base_url.startswith("https://")
