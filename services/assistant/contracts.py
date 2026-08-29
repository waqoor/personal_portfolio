"""Public integration contracts for assistant retrieval and audit persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PublishedContentDocument:
    source_id: str
    content_type: str
    title: str
    excerpt: str
    canonical_url: str
    relevance: float = 0.0
    published_at: datetime | None = None
    is_published: bool = True
    is_public: bool = True
    is_hidden: bool = False
    is_archived: bool = False
    is_approved: bool = True
    is_indexable: bool = True
    allow_ai: bool = True


class PublishedContentProvider(Protocol):
    """Implemented by domain services without exposing their repositories/models."""

    async def search_published(
        self, query: str, *, limit: int
    ) -> list[PublishedContentDocument]: ...


@dataclass(frozen=True, slots=True)
class NewAssistantAuditEvent:
    id: str
    question_fingerprint: str
    status: str
    source_count: int
    duration_ms: int
    contained_redacted_pii: bool
    provider_request_id: str | None
    created_at: datetime


class AssistantAuditRepository(Protocol):
    async def record_event(self, event: NewAssistantAuditEvent) -> None: ...
