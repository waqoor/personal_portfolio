from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from packages.python.common.models import PublicationStatus


class Publishable(Protocol):
    status: PublicationStatus
    is_visible: bool
    noindex: bool
    published_at: datetime | None
    archived_at: datetime | None


class PublicationPolicy:
    """Single lifecycle authority reused by all domain sub-services."""

    @staticmethod
    def is_public(entity: Publishable) -> bool:
        return (
            entity.status is PublicationStatus.PUBLISHED
            and entity.is_visible
            and entity.archived_at is None
        )

    @staticmethod
    def apply(entity: Publishable, status: PublicationStatus) -> None:
        now = datetime.now(UTC)
        entity.status = status
        if status is PublicationStatus.PUBLISHED:
            entity.published_at = entity.published_at or now
            entity.archived_at = None
            entity.is_visible = True
        elif status is PublicationStatus.HIDDEN:
            entity.is_visible = False
            entity.archived_at = None
        elif status is PublicationStatus.ARCHIVED:
            entity.is_visible = False
            entity.archived_at = now
        elif status is PublicationStatus.DRAFT:
            entity.is_visible = False
            entity.archived_at = None
