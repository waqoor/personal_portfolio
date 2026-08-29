from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.repository import AuthRepository
from apps.api.auth.service import AuthService
from packages.python.clients.database import DatabaseClient
from packages.python.clients.repository_metadata import RepositoryMetadataClient
from packages.python.clients.storage import StorageClient
from packages.python.common.repository import SQLAlchemyTransactionManager
from packages.python.common.security import PasswordService
from packages.python.common.settings import Settings
from services.content.registry import HomepageSectionRegistry
from services.content.repository import ContentRepository
from services.content.service import ContentService, HomepageComposer
from services.identity.repository import IdentityRepository
from services.identity.service import IdentityService
from services.portfolio.repository import PortfolioRepository
from services.portfolio.service import PortfolioService


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: DatabaseClient = request.app.state.database_client
    async with database.session() as session:
        yield session


def get_auth_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    settings: Settings = request.app.state.settings
    password_service: PasswordService = request.app.state.password_service
    return AuthService(
        AuthRepository(session),
        SQLAlchemyTransactionManager(session),
        settings,
        password_service,
        request.app.state.rate_limiter,
    )


def get_identity_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IdentityService:
    storage: StorageClient = request.app.state.storage_client
    return IdentityService(
        IdentityRepository(session),
        SQLAlchemyTransactionManager(session),
        storage,
        request.app.state.settings,
    )


def get_portfolio_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PortfolioService:
    storage: StorageClient = request.app.state.storage_client
    repository_metadata: RepositoryMetadataClient = request.app.state.repository_metadata_client
    return PortfolioService(
        PortfolioRepository(session),
        SQLAlchemyTransactionManager(session),
        storage,
        request.app.state.settings,
        repository_metadata,
    )


def get_content_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ContentService:
    storage: StorageClient = request.app.state.storage_client
    registry: HomepageSectionRegistry = request.app.state.homepage_section_registry
    return ContentService(
        ContentRepository(session),
        SQLAlchemyTransactionManager(session),
        storage,
        request.app.state.settings,
        registry,
    )


def get_homepage_composer(
    request: Request,
    content: Annotated[ContentService, Depends(get_content_service)],
    identity: Annotated[IdentityService, Depends(get_identity_service)],
    portfolio: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> HomepageComposer:
    registry: HomepageSectionRegistry = request.app.state.homepage_section_registry
    settings: Settings = request.app.state.settings
    return HomepageComposer(
        content,
        identity,
        portfolio,
        registry,
        runtime_feature_caps={
            "assistant": settings.assistant_enabled,
            "contact": settings.contact_enabled,
            "sponsorship": settings.sponsorship_enabled,
        },
        assistant_max_question_length=settings.assistant_max_question_chars,
    )
