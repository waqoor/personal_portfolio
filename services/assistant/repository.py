"""SQLAlchemy adapter for assistant audit metadata (never prompts or answers)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from services.assistant.contracts import NewAssistantAuditEvent
from services.assistant.models import AssistantAuditEvent


class SQLAlchemyAssistantAuditRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record_event(self, event: NewAssistantAuditEvent) -> None:
        async with self._session_factory() as session:
            session.add(
                AssistantAuditEvent(
                    id=event.id,
                    question_fingerprint=event.question_fingerprint,
                    status=event.status,
                    source_count=event.source_count,
                    duration_ms=event.duration_ms,
                    contained_redacted_pii=event.contained_redacted_pii,
                    provider_request_id=event.provider_request_id,
                    created_at=event.created_at,
                )
            )
            await session.commit()
