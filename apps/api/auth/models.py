from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.python.common.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AdminRole(enum.StrEnum):
    OWNER = "owner"
    EDITOR = "editor"


def admin_role_type() -> Enum:
    return Enum(
        AdminRole,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=16,
    )


class AdminUser(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[AdminRole] = mapped_column(
        admin_role_type(), default=AdminRole.EDITOR, server_default=AdminRole.EDITOR.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list[AdminSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AdminSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "admin_sessions"
    __table_args__ = (
        Index("ix_admin_sessions_user_active", "admin_user_id", "expires_at", "revoked_at"),
    )

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admin_users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[AdminUser] = relationship(back_populates="sessions", lazy="joined")


class LoginAttempt(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "login_attempts"
    __table_args__ = (
        Index(
            "ix_login_attempts_throttle",
            "identifier_digest",
            "ip_digest",
            "occurred_at",
            "succeeded",
        ),
        Index("ix_login_attempts_identifier_recent", "identifier_digest", "occurred_at"),
        Index("ix_login_attempts_ip_recent", "ip_digest", "occurred_at"),
    )

    identifier_digest: Mapped[str] = mapped_column(String(64))
    ip_digest: Mapped[str] = mapped_column(String(64))
    succeeded: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
