from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.python.clients.storage import StorageClient
from packages.python.common.repository import SQLAlchemyTransactionManager
from packages.python.common.settings import Settings
from services.identity.contracts import IdentityPublicReader, IdentityPublicReaderFactory
from services.identity.repository import IdentityRepository
from services.identity.service import IdentityService


def build_identity_public_reader(
    session_factory: async_sessionmaker[AsyncSession],
    storage: StorageClient,
    settings: Settings,
) -> IdentityPublicReaderFactory:
    @asynccontextmanager
    async def reader() -> AsyncIterator[IdentityPublicReader]:
        async with session_factory() as session:
            yield IdentityService(
                IdentityRepository(session),
                SQLAlchemyTransactionManager(session),
                storage,
                settings,
            )

    return reader
