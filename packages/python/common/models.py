from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PublicationStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    HIDDEN = "hidden"
    ARCHIVED = "archived"


def publication_status_type() -> Enum:
    return Enum(
        PublicationStatus,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=16,
    )


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SeededMixin:
    seed_key: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    seed_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    seeded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PublishableMixin:
    status: Mapped[PublicationStatus] = mapped_column(
        publication_status_type(),
        default=PublicationStatus.DRAFT,
        server_default=PublicationStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    noindex: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
