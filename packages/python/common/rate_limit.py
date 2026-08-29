"""Database-backed fixed-window limiter shared by abuse-sensitive services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import CheckConstraint, DateTime, Integer, String, case, delete, or_, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from packages.python.common.models import Base


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    __table_args__ = (
        CheckConstraint("request_count > 0", name="ck_rate_limit_request_count_positive"),
    )

    bucket_key: Mapped[str] = mapped_column(String(160), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


@dataclass(frozen=True, slots=True)
class RateLimitRequest:
    namespace: str
    identity_hash: str
    limit: int
    window_seconds: int


class DatabaseRateLimiter:
    """Atomic in PostgreSQL and SQLite; all requested buckets commit together."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def consume(
        self,
        requests: tuple[RateLimitRequest, ...],
        *,
        now: datetime | None = None,
    ) -> bool:
        if not requests:
            return True
        checked_at = now or datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            for request in _deduplicate(requests):
                allowed = await self._consume_one(session, request, checked_at)
                if not allowed:
                    await session.rollback()
                    return False
        return True

    async def _consume_one(
        self,
        session: AsyncSession,
        request: RateLimitRequest,
        checked_at: datetime,
    ) -> bool:
        bucket_key = f"{request.namespace}:{request.identity_hash}"
        cutoff = checked_at - timedelta(seconds=request.window_seconds)
        dialect = session.bind.dialect.name if session.bind is not None else "unknown"
        if dialect in {"postgresql", "sqlite"}:
            insert_factory = postgres_insert if dialect == "postgresql" else sqlite_insert
            insert_statement = insert_factory(RateLimitBucket).values(
                bucket_key=bucket_key,
                window_started_at=checked_at,
                request_count=1,
                updated_at=checked_at,
            )
            expired = RateLimitBucket.window_started_at <= cutoff
            statement = insert_statement.on_conflict_do_update(
                index_elements=[RateLimitBucket.bucket_key],
                set_={
                    "window_started_at": case(
                        (expired, checked_at), else_=RateLimitBucket.window_started_at
                    ),
                    "request_count": case((expired, 1), else_=RateLimitBucket.request_count + 1),
                    "updated_at": checked_at,
                },
                where=or_(expired, RateLimitBucket.request_count < request.limit),
            ).returning(RateLimitBucket.bucket_key)
            upsert_result = await session.execute(statement)
            return upsert_result.scalar_one_or_none() is not None

        select_result = await session.execute(
            select(RateLimitBucket)
            .where(RateLimitBucket.bucket_key == bucket_key)
            .with_for_update()
        )
        bucket = select_result.scalar_one_or_none()
        if bucket is None:
            session.add(
                RateLimitBucket(
                    bucket_key=bucket_key,
                    window_started_at=checked_at,
                    request_count=1,
                    updated_at=checked_at,
                )
            )
            return True
        window_started_at = _as_aware(bucket.window_started_at)
        if window_started_at <= cutoff:
            bucket.window_started_at = checked_at
            bucket.request_count = 1
            bucket.updated_at = checked_at
            return True
        if bucket.request_count >= request.limit:
            return False
        bucket.request_count += 1
        bucket.updated_at = checked_at
        return True

    async def reset(self, *, namespace: str, identity_hash: str) -> None:
        """Clear one exact bucket without decaying unrelated abuse dimensions."""

        bucket_key = f"{namespace}:{identity_hash}"
        async with self._session_factory() as session, session.begin():
            await session.execute(
                delete(RateLimitBucket).where(RateLimitBucket.bucket_key == bucket_key)
            )

def _deduplicate(requests: tuple[RateLimitRequest, ...]) -> tuple[RateLimitRequest, ...]:
    unique: dict[tuple[str, str], RateLimitRequest] = {}
    for request in requests:
        unique[(request.namespace, request.identity_hash)] = request
    return tuple(unique.values())


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
