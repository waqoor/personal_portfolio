"""Privacy-minimized assistant operational audit model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.python.common.models import Base


class AssistantAuditEvent(Base):
    __tablename__ = "assistant_audit_events"
    __table_args__ = (
        Index("ix_assistant_audit_events_created", "created_at"),
        Index("ix_assistant_audit_events_status_created", "status", "created_at"),
        CheckConstraint("source_count >= 0", name="ck_assistant_source_count_nonnegative"),
        CheckConstraint("duration_ms >= 0", name="ck_assistant_duration_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    contained_redacted_pii: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
