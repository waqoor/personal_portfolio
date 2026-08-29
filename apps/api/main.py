"""FastAPI composition root for all independently owned domain services."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from typing import Protocol

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from apps.api.auth.router import router as auth_router
from apps.api.errors import register_error_handlers
from apps.api.health import router as health_router
from apps.api.middleware import (
    ContentLengthLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from packages.python.clients.ai import AIProviderClient
from packages.python.clients.database import DatabaseClient
from packages.python.clients.email import EmailClient
from packages.python.clients.github_repository import GitHubRepositoryMetadataClient
from packages.python.clients.openai_compatible_ai import OpenAICompatibleAIProviderClient
from packages.python.clients.repository_metadata import RepositoryMetadataClient
from packages.python.clients.smtp_email import SMTPEmailClient
from packages.python.clients.storage import LocalStorageClient, StorageClient
from packages.python.common.logging import configure_logging
from packages.python.common.rate_limit import DatabaseRateLimiter
from packages.python.common.security import PasswordService
from packages.python.common.settings import Settings
from services.assistant.contracts import PublishedContentProvider
from services.assistant.repository import SQLAlchemyAssistantAuditRepository
from services.assistant.retrieval import PublishedContentRegistry
from services.assistant.router import router as assistant_router
from services.assistant.service import AssistantService, AssistantServiceConfig
from services.content.composition import build_content_public_reader
from services.content.registry import HomepageSectionRegistry
from services.content.router import admin_router as content_admin_router
from services.content.router import public_router as content_public_router
from services.discovery.contracts import DiscoveryContentProvider
from services.discovery.registry import DiscoveryContentRegistry
from services.discovery.router import api_router as discovery_api_router
from services.discovery.router import crawler_router
from services.discovery.service import DiscoveryService, SiteIdentity
from services.engagement.discovery import EngagementDiscoveryProvider
from services.engagement.repository import SQLAlchemyEngagementRepository
from services.engagement.router import admin_router as engagement_admin_router
from services.engagement.router import public_router as engagement_public_router
from services.engagement.schemas import ContactNotificationBatchResult
from services.engagement.service import (
    ContactService,
    ContactServiceConfig,
    EngagementAdminService,
    SponsorshipService,
)
from services.identity.composition import build_identity_public_reader
from services.identity.router import admin_router as identity_admin_router
from services.identity.router import public_router as identity_public_router
from services.portfolio.composition import build_portfolio_public_reader
from services.portfolio.router import admin_router as portfolio_admin_router
from services.portfolio.router import public_router as portfolio_public_router
from services.public_catalog import CanonicalPublicContentProvider

logger = logging.getLogger(__name__)


class ContactNotificationProcessor(Protocol):
    async def process_due_notifications(self, *, limit: int) -> ContactNotificationBatchResult: ...


async def _run_contact_notification_worker(
    service: ContactNotificationProcessor,
    *,
    stop_event: asyncio.Event,
    poll_seconds: int,
    batch_size: int,
) -> None:
    """Poll the durable outbox; database leases make multiple API replicas safe."""

    while not stop_event.is_set():
        with suppress(TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=poll_seconds)
        if stop_event.is_set():
            return
        try:
            result = await service.process_due_notifications(limit=batch_size)
            if result.selected_count:
                logger.info(
                    "contact_notification_batch_processed",
                    extra={
                        "selected_count": result.selected_count,
                        "sent_count": result.sent_count,
                        "not_sent_count": result.not_sent_by_this_worker_count,
                    },
                )
        except Exception:
            logger.exception("contact_notification_batch_failed")


async def _safe_close(name: str, close: Callable[[], Awaitable[None]]) -> None:
    try:
        await close()
    except Exception as exc:
        logger.error(
            "application_shutdown_component_failed",
            extra={"component": name, "error_type": type(exc).__name__},
        )


def create_app(
    settings: Settings | None = None,
    *,
    database_client: DatabaseClient | None = None,
    email_client: EmailClient | None = None,
    ai_provider_client: AIProviderClient | None = None,
    storage_client: StorageClient | None = None,
    repository_metadata_client: RepositoryMetadataClient | None = None,
    published_content_providers: tuple[PublishedContentProvider, ...] = (),
    discovery_content_providers: tuple[DiscoveryContentProvider, ...] = (),
) -> FastAPI:
    runtime_settings = settings or Settings()
    configure_logging(
        level=runtime_settings.log_level,
        json_logs=runtime_settings.json_logs,
    )
    database = database_client or DatabaseClient(
        runtime_settings.database_url,
        pool_size=runtime_settings.db_pool_size,
        max_overflow=runtime_settings.db_max_overflow,
        pool_timeout_seconds=runtime_settings.db_pool_timeout_seconds,
    )
    configured_email_client = email_client or _build_email_client(runtime_settings)
    configured_ai_client = ai_provider_client or _build_ai_client(runtime_settings)
    configured_storage_client = storage_client or LocalStorageClient(runtime_settings.storage_root)
    configured_repository_metadata_client = (
        repository_metadata_client
        or GitHubRepositoryMetadataClient(
            token=(
                runtime_settings.github_api_token.get_secret_value()
                if runtime_settings.github_api_token
                else None
            ),
            timeout_seconds=runtime_settings.repository_metadata_timeout_seconds,
        )
    )
    owns_repository_metadata_client = repository_metadata_client is None
    homepage_registry = HomepageSectionRegistry(runtime_settings.featured_project_limit)
    canonical_content_provider = CanonicalPublicContentProvider(
        identity_reader=build_identity_public_reader(
            database.session_factory, configured_storage_client, runtime_settings
        ),
        portfolio_reader=build_portfolio_public_reader(
            database.session_factory, configured_storage_client, runtime_settings
        ),
        content_reader=build_content_public_reader(
            database.session_factory,
            configured_storage_client,
            runtime_settings,
            homepage_registry,
        ),
        settings=runtime_settings,
    )
    effective_published_providers = published_content_providers or (canonical_content_provider,)
    engagement_repository = SQLAlchemyEngagementRepository(database.session_factory)
    rate_limiter = DatabaseRateLimiter(database.session_factory)
    contact_service = ContactService(
        repository=engagement_repository,
        email_client=configured_email_client,
        rate_limiter=rate_limiter,
        config=ContactServiceConfig(
            enabled=runtime_settings.contact_enabled,
            email_enabled=runtime_settings.email_enabled,
            privacy_hash_secret=runtime_settings.privacy_hash_secret.get_secret_value(),
            rate_limit_window_seconds=runtime_settings.contact_rate_limit_window_seconds,
            ip_limit=runtime_settings.contact_ip_limit,
            email_limit=runtime_settings.contact_email_limit,
            max_links=runtime_settings.contact_max_links,
            response_time_label=runtime_settings.contact_response_time_label,
        ),
        feature_flags=canonical_content_provider,
    )
    sponsorship_service = SponsorshipService(
        repository=engagement_repository,
        enabled=runtime_settings.sponsorship_enabled,
        feature_flags=canonical_content_provider,
    )
    effective_discovery_providers = discovery_content_providers or (
        canonical_content_provider,
        EngagementDiscoveryProvider(
            contact=contact_service,
            sponsorship=sponsorship_service,
        ),
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        del application
        logger.info("application_startup", extra={"environment": runtime_settings.environment})
        notification_stop = asyncio.Event()
        notification_task: asyncio.Task[None] | None = None
        if runtime_settings.email_enabled and configured_email_client is not None:
            notification_task = asyncio.create_task(
                _run_contact_notification_worker(
                    contact_service,
                    stop_event=notification_stop,
                    poll_seconds=runtime_settings.contact_notification_poll_seconds,
                    batch_size=runtime_settings.contact_notification_batch_size,
                ),
                name="contact-notification-outbox",
            )
        try:
            yield
        finally:
            logger.info("application_shutdown_started")
            notification_stop.set()
            if notification_task is not None:
                await notification_task
            if configured_email_client is not None:
                await _safe_close("email_client", configured_email_client.close)
            if configured_ai_client is not None:
                await _safe_close("ai_provider_client", configured_ai_client.close)
            if owns_repository_metadata_client:
                await _safe_close(
                    "repository_metadata_client",
                    configured_repository_metadata_client.close,
                )
            await _safe_close("database", database.dispose)
            logger.info("application_shutdown_complete")

    docs_url = "/docs" if runtime_settings.docs_enabled else None
    app = FastAPI(
        title=runtime_settings.app_name,
        version="1.0.0",
        docs_url=docs_url,
        redoc_url=None,
        openapi_url="/openapi.json" if runtime_settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = runtime_settings
    app.state.database_client = database
    app.state.email_client = configured_email_client
    app.state.ai_provider_client = configured_ai_client
    app.state.storage_client = configured_storage_client
    app.state.repository_metadata_client = configured_repository_metadata_client
    app.state.password_service = PasswordService()
    app.state.homepage_section_registry = homepage_registry
    app.state.rate_limiter = rate_limiter
    app.state.contact_service = contact_service
    app.state.sponsorship_service = sponsorship_service
    app.state.engagement_admin_service = EngagementAdminService(
        engagement_repository, contact_service
    )
    app.state.assistant_service = AssistantService(
        content_registry=PublishedContentRegistry(effective_published_providers),
        provider_client=configured_ai_client,
        audit_repository=SQLAlchemyAssistantAuditRepository(database.session_factory),
        rate_limiter=rate_limiter,
        config=AssistantServiceConfig(
            enabled=runtime_settings.assistant_enabled,
            privacy_hash_secret=runtime_settings.privacy_hash_secret.get_secret_value(),
            rate_limit_window_seconds=runtime_settings.assistant_rate_limit_window_seconds,
            ip_limit=runtime_settings.assistant_ip_limit,
            max_question_chars=runtime_settings.assistant_max_question_chars,
            max_sources=runtime_settings.assistant_max_sources,
            max_context_chars=runtime_settings.assistant_max_context_chars,
            max_output_tokens=runtime_settings.assistant_max_output_tokens,
        ),
        feature_flags=canonical_content_provider,
        configuration_reader=canonical_content_provider,
    )
    app.state.discovery_service = DiscoveryService(
        registry=DiscoveryContentRegistry(effective_discovery_providers),
        public_site_url=runtime_settings.public_base_url,
        configuration_reader=canonical_content_provider,
        identity=SiteIdentity(
            site_name=runtime_settings.site_name,
            owner_name=runtime_settings.site_owner_name,
            owner_headline=runtime_settings.site_owner_headline,
            default_title=runtime_settings.site_default_title,
            description=runtime_settings.site_description,
            locale=runtime_settings.site_locale,
            language=runtime_settings.site_language,
            social_image_url=runtime_settings.site_social_image_url,
            verified_same_as_urls=tuple(runtime_settings.verified_same_as_urls),
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Content-Type",
            "Idempotency-Key",
            "X-CSRF-Token",
            "X-Request-ID",
        ],
        expose_headers=["Retry-After", "X-Request-ID"],
        max_age=600,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=runtime_settings.allowed_hosts)
    app.add_middleware(
        SecurityHeadersMiddleware,
        content_security_policy=runtime_settings.content_security_policy,
        production=runtime_settings.environment == "production",
    )
    app.add_middleware(
        ContentLengthLimitMiddleware,
        max_bytes=runtime_settings.max_request_bytes,
        route_limits={
            "/api/v1/contact": 64 * 1024,
            "/api/v1/assistant": 32 * 1024,
            "/api/v1/auth": 64 * 1024,
        },
    )
    app.add_middleware(RequestContextMiddleware)

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(identity_public_router)
    app.include_router(identity_admin_router)
    app.include_router(portfolio_public_router)
    app.include_router(portfolio_admin_router)
    app.include_router(content_public_router)
    app.include_router(content_admin_router)
    app.include_router(engagement_public_router)
    app.include_router(engagement_admin_router)
    app.include_router(assistant_router)
    app.include_router(discovery_api_router)
    app.include_router(crawler_router)
    return app


def _build_email_client(settings: Settings) -> EmailClient | None:
    if not settings.email_enabled:
        return None
    return SMTPEmailClient(
        host=settings.smtp_host or "",
        port=settings.smtp_port,
        from_address=str(settings.email_from_address or ""),
        contact_recipient=str(settings.contact_notification_to or ""),
        username=settings.smtp_username,
        password=(settings.smtp_password.get_secret_value() if settings.smtp_password else None),
        use_starttls=settings.smtp_use_starttls,
        use_ssl=settings.smtp_use_ssl,
        timeout_seconds=settings.smtp_timeout_seconds,
    )


def _build_ai_client(settings: Settings) -> AIProviderClient | None:
    if not settings.assistant_enabled:
        return None
    if settings.ai_provider_api_key is None or settings.ai_model is None:
        return None
    return OpenAICompatibleAIProviderClient(
        base_url=settings.ai_provider_base_url,
        api_key=settings.ai_provider_api_key.get_secret_value(),
        model=settings.ai_model,
        timeout_seconds=settings.ai_timeout_seconds,
        max_retries=settings.ai_max_retries,
    )


app = create_app()
