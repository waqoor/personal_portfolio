"""SQLAlchemy engine and session lifecycle boundary."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def normalize_async_database_url(database_url: str) -> str:
    """Normalize common PostgreSQL URLs to SQLAlchemy's async driver URL."""

    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return database_url


class DatabaseClient:
    """Own the database engine, pool, sessions, diagnostics, and cleanup."""

    def __init__(
        self,
        database_url: str,
        *,
        pool_size: int = 10,
        max_overflow: int = 10,
        pool_timeout_seconds: float = 10.0,
        pool_recycle_seconds: int = 1800,
        echo: bool = False,
    ) -> None:
        normalized_url = normalize_async_database_url(database_url)
        engine_options: dict[str, object] = {
            "echo": echo,
            "pool_pre_ping": True,
        }
        if not normalized_url.startswith("sqlite"):
            engine_options.update(
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout_seconds,
                pool_recycle=pool_recycle_seconds,
            )
        self._engine: AsyncEngine = create_async_engine(normalized_url, **engine_options)
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a session and guarantee rollback/close on exceptional paths."""

        async with self._session_factory() as session:
            try:
                yield session
            except BaseException:
                await session.rollback()
                raise

    async def health_check(self) -> bool:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:  # diagnostics normalize all driver-specific failures
            return False
        return True

    async def dispose(self) -> None:
        await self._engine.dispose()
