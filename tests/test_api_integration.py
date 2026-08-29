from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import func, select

from apps.api.main import create_app
from packages.python.clients.database import DatabaseClient
from packages.python.common.settings import Settings
from services.engagement.models import ContactSubmission


def _settings(database: DatabaseClient) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url=str(database.engine.url),
        public_base_url="https://portfolio.example",
        api_public_url="https://portfolio.example/api",
        allowed_origins=["https://portfolio.example"],
        allowed_hosts=["testserver", "portfolio.example"],
        auth_secret="test-auth-secret-with-at-least-32-characters",
        privacy_hash_secret="test-privacy-secret-with-at-least-32-characters",
        contact_ip_limit=1,
        contact_email_limit=1,
        email_enabled=False,
        assistant_enabled=False,
    )


@pytest.fixture
async def api_client(database_client: DatabaseClient) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(_settings(database_client), database_client=database_client)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_contact_api_persists_and_returns_security_headers(
    api_client: httpx.AsyncClient,
    database_client: DatabaseClient,
) -> None:
    response = await api_client.post(
        "/api/v1/contact",
        headers={"Idempotency-Key": "api-request-key-1", "X-Request-ID": "request-12345"},
        json={
            "name": "API Visitor",
            "email": "visitor@example.com",
            "category": "collaboration",
            "subject": "Production collaboration",
            "message": "I would like to discuss a production collaboration in detail.",
            "consent": True,
            "website": "",
        },
    )

    assert response.status_code == 202
    assert response.headers["x-request-id"] == "request-12345"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    async with database_client.session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(ContactSubmission))
    assert count == 1


@pytest.mark.asyncio
async def test_validation_error_does_not_echo_private_input(
    api_client: httpx.AsyncClient,
) -> None:
    private_message = "secret-value-that-must-not-be-echoed"
    response = await api_client.post(
        "/api/v1/contact",
        json={
            "name": "X",
            "email": "not-an-email",
            "message": private_message,
            "consent": False,
        },
    )

    assert response.status_code == 422
    assert private_message not in response.text
    assert "not-an-email" not in response.text
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_rate_limit_has_retry_after_header(api_client: httpx.AsyncClient) -> None:
    payload = {
        "name": "Rate Limited Visitor",
        "email": "rate@example.com",
        "category": "general",
        "message": "This valid message is long enough for contact validation.",
        "consent": True,
    }
    first = await api_client.post("/api/v1/contact", json=payload)
    second = await api_client.post(
        "/api/v1/contact",
        json={**payload, "email": "different@example.com"},
    )

    assert first.status_code == 202
    assert second.status_code == 429
    assert second.headers["retry-after"] == "3600"


@pytest.mark.asyncio
async def test_health_and_crawler_endpoints(api_client: httpx.AsyncClient) -> None:
    live = await api_client.get("/health/live")
    ready = await api_client.get("/health/ready")
    sitemap = await api_client.get("/sitemap.xml")
    robots = await api_client.get("/robots.txt")
    llms = await api_client.get("/llms.txt")

    assert live.status_code == 200
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"] is True
    assert sitemap.headers["content-type"].startswith("application/xml")
    assert "https://portfolio.example/" in sitemap.text
    assert "Sitemap: https://portfolio.example/sitemap.xml" in robots.text
    assert "Do not infer private" in llms.text


@pytest.mark.asyncio
async def test_cors_is_restrictive_and_body_limit_is_enforced(
    api_client: httpx.AsyncClient,
) -> None:
    allowed = await api_client.options(
        "/api/v1/contact",
        headers={
            "Origin": "https://portfolio.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    denied = await api_client.options(
        "/api/v1/contact",
        headers={
            "Origin": "https://evil.invalid",
            "Access-Control-Request-Method": "POST",
        },
    )
    oversized = await api_client.post(
        "/api/v1/contact",
        headers={"Content-Length": "2000000"},
        content=b"{}",
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://portfolio.example"
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
    assert oversized.status_code == 413
