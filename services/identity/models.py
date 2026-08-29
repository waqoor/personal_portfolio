from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.python.common.models import (
    Base,
    PublishableMixin,
    SeededMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Profile(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "profiles"
    __table_args__ = (
        Index(
            "uq_profiles_primary",
            "is_primary",
            unique=True,
            postgresql_where=text("is_primary"),
            sqlite_where=text("is_primary = 1"),
        ),
        CheckConstraint(
            "(primary_cta_label IS NULL AND primary_cta_url IS NULL) OR "
            "(primary_cta_label IS NOT NULL AND length(trim(primary_cta_label)) > 0 "
            "AND primary_cta_url IS NOT NULL)",
            name="ck_profile_primary_cta_pair",
        ),
        CheckConstraint(
            "(secondary_cta_label IS NULL AND secondary_cta_url IS NULL) OR "
            "(secondary_cta_label IS NOT NULL AND length(trim(secondary_cta_label)) > 0 "
            "AND secondary_cta_url IS NOT NULL)",
            name="ck_profile_secondary_cta_pair",
        ),
    )

    full_name: Mapped[str] = mapped_column(String(160))
    headline: Mapped[str] = mapped_column(String(240))
    short_bio: Mapped[str] = mapped_column(Text)
    long_bio: Mapped[str | None] = mapped_column(Text)
    public_location: Mapped[str | None] = mapped_column(String(160))
    availability_status: Mapped[str | None] = mapped_column(String(80))
    availability_detail: Mapped[str | None] = mapped_column(String(300))
    public_email: Mapped[str | None] = mapped_column(String(320))
    primary_cta_label: Mapped[str | None] = mapped_column(String(80))
    primary_cta_url: Mapped[str | None] = mapped_column(String(2048))
    secondary_cta_label: Mapped[str | None] = mapped_column(String(80))
    secondary_cta_url: Mapped[str | None] = mapped_column(String(2048))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    portraits: Mapped[list[PortraitAsset]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )
    resume_versions: Mapped[list[ResumeVersion]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )
    social_links: Mapped[list[SocialLink]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )


class PortraitAsset(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, Base):
    __tablename__ = "portrait_assets"
    __table_args__ = (
        Index(
            "uq_portrait_primary_per_profile",
            "profile_id",
            unique=True,
            postgresql_where=text("is_primary AND is_active"),
            sqlite_where=text("is_primary = 1 AND is_active = 1"),
        ),
        Index("ix_portrait_assets_profile_order", "profile_id", "sort_order"),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    alt_text: Mapped[str] = mapped_column(String(300))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    profile: Mapped[Profile] = relationship(back_populates="portraits")


class ResumeVersion(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "resume_versions"
    __table_args__ = (
        Index(
            "uq_resume_current",
            "is_current",
            unique=True,
            postgresql_where=text("is_current"),
            sqlite_where=text("is_current = 1"),
        ),
        Index("ix_resume_versions_profile_created", "profile_id", "created_at"),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    version_label: Mapped[str] = mapped_column(String(120))
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(100), default="application/pdf")
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    effective_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    download_name: Mapped[str] = mapped_column(String(255), default="resume.pdf")

    profile: Mapped[Profile] = relationship(back_populates="resume_versions")


class SocialLink(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, Base):
    __tablename__ = "social_links"
    __table_args__ = (Index("ix_social_links_profile_order", "profile_id", "sort_order"),)

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(2048))
    handle: Mapped[str | None] = mapped_column(String(160))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    profile: Mapped[Profile] = relationship(back_populates="social_links")
