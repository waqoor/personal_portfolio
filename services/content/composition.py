from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.python.clients.storage import StorageClient
from packages.python.common.repository import SQLAlchemyTransactionManager
from packages.python.common.settings import Settings
from services.content.contracts import ContentPublicReader, ContentPublicReaderFactory
from services.content.registry import HomepageSectionRegistry
from services.content.repository import ContentRepository
from services.content.service import ContentService


def build_content_public_reader(
    session_factory: async_sessionmaker[AsyncSession],
    storage: StorageClient,
    settings: Settings,
    registry: HomepageSectionRegistry,
) -> ContentPublicReaderFactory:
    @asynccontextmanager
    async def reader() -> AsyncIterator[ContentPublicReader]:
        async with session_factory() as session:
            yield ContentService(
                ContentRepository(session),
                SQLAlchemyTransactionManager(session),
                storage,
                settings,
                registry,
            )

    return reader
