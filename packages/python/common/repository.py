from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, Protocol, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.python.common.models import Base


class TransactionManager(Protocol):
    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class SQLAlchemyTransactionManager:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()


ModelT = TypeVar("ModelT", bound=Base)


class SQLAlchemyRepository(Generic[ModelT]):  # noqa: UP046
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)

    async def list_query(
        self, statement: Select[tuple[ModelT]], *, limit: int, offset: int
    ) -> Sequence[ModelT]:
        result = await self.session.scalars(statement.limit(limit).offset(offset))
        return result.unique().all()

    async def count(self, statement: Select[tuple[ModelT]]) -> int:
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        return int((await self.session.scalar(count_statement)) or 0)
