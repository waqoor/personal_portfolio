"""Engagement-owned persistence models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.python.common.models import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ContactSubmission(Base):
    __tablename__ = "contact_submissions"
    __table_args__ = (
        Index("ix_contact_submissions_created_at", "created_at"),
        Index("ix_contact_submissions_email_hash_created", "email_hash", "created_at"),
        Index("ix_contact_submissions_status_created", "status", "created_at"),
        CheckConstraint(
            "category IN ('general', 'project', 'collaboration', "
            "'speaking', 'sponsorship', 'other')",
            name="ck_contact_submission_category",
        ),
        CheckConstraint(
            "status IN ('new', 'read', 'closed', 'spam')",
            name="ck_contact_submission_status",
        ),
        CheckConstraint(
            "notification_status IN "
            "('pending', 'disabled', 'sent', 'failed', 'retrying', 'terminal')",
            name="ck_contact_notification_status",
        ),
        CheckConstraint("consent = true", name="ck_contact_submission_consent"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    consent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="new", nullable=False)
    notification_status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    notification_error_code: Mapped[str | None] = mapped_column(String(64))
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    payload_digest: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    notification_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notification_outbox: Mapped[ContactNotificationOutbox | None] = relationship(
        back_populates="submission", cascade="all, delete-orphan", uselist=False
    )


class ContactNotificationOutbox(Base):
    """Durable, retryable delivery intent created atomically with a contact submission."""

    __tablename__ = "contact_notification_outbox"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'retrying', 'sent', 'terminal', 'disabled')",
            name="ck_contact_outbox_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_contact_outbox_attempts"),
        Index("ix_contact_outbox_due", "status", "next_attempt_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("contact_submissions.id", ondelete="CASCADE"), unique=True
    )
    provider_idempotency_key: Mapped[str] = mapped_column(String(96), unique=True)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    submission: Mapped[ContactSubmission] = relationship(back_populates="notification_outbox")


class SponsorshipOption(Base):
    __tablename__ = "sponsorship_options"
    __table_args__ = (
        Index(
            "ix_sponsorship_options_public_order",
            "is_published",
            "is_archived",
            "sort_order",
        ),
        CheckConstraint(
            "amount_minor IS NULL OR amount_minor >= 0",
            name="ck_sponsorship_amount_nonnegative",
        ),
        CheckConstraint(
            "(amount_minor IS NULL AND currency IS NULL) OR "
            "(amount_minor IS NOT NULL AND currency IS NOT NULL)",
            name="ck_sponsorship_amount_currency_pair",
        ),
        CheckConstraint(
            "recurrence IS NULL OR recurrence IN ('one_time', 'monthly', 'yearly')",
            name="ck_sponsorship_recurrence",
        ),
        CheckConstraint("sort_order >= 0", name="ck_sponsorship_sort_order_nonnegative"),
        CheckConstraint(
            "destination_url LIKE 'https://%'",
            name="ck_sponsorship_destination_https",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    cta_label: Mapped[str] = mapped_column(String(80), nullable=False)
    destination_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    amount_minor: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(3))
    recurrence: Mapped[str | None] = mapped_column(String(20))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nofollow: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
