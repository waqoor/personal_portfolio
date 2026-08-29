from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from packages.python.clients.storage import StorageClient
from packages.python.common.repository import SQLAlchemyTransactionManager
from packages.python.common.settings import Settings
from services.portfolio.contracts import PortfolioPublicReader, PortfolioPublicReaderFactory
from services.portfolio.repository import PortfolioRepository
from services.portfolio.service import PortfolioService


def build_portfolio_public_reader(
    session_factory: async_sessionmaker[AsyncSession],
    storage: StorageClient,
    settings: Settings,
) -> PortfolioPublicReaderFactory:
    @asynccontextmanager
    async def reader() -> AsyncIterator[PortfolioPublicReader]:
        async with session_factory() as session:
            yield PortfolioService(
                PortfolioRepository(session),
                SQLAlchemyTransactionManager(session),
                storage,
                settings,
            )

    return reader
