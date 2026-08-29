from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.python.common.models import (
    Base,
    PublishableMixin,
    SeededMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


def json_type() -> JSON:
    return JSON().with_variant(JSONB(), "postgresql")


class HomepageSectionType(enum.StrEnum):
    HERO = "hero"
    RESUME = "resume"
    AVAILABILITY = "availability"
    WHAT_I_BUILD = "what_i_build"
    CATEGORIES = "categories"
    SELECTED_WORK = "selected_work"
    METRICS = "metrics"
    TESTIMONIALS = "testimonials"
    SECTORS = "sectors"
    SKILLS = "skills"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATIONS = "certifications"
    OPEN_SOURCE = "open_source"
    SPONSORSHIP = "sponsorship"
    WRITING = "writing"
    ASSISTANT = "assistant"
    CONTACT = "contact"
    SOCIAL_LINKS = "social_links"
    EDITORIAL = "editorial"


class NavigationLocation(enum.StrEnum):
    HEADER = "header"
    FOOTER = "footer"


def homepage_section_type() -> Enum:
    return Enum(
        HomepageSectionType,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=32,
    )


def navigation_location_type() -> Enum:
    return Enum(
        NavigationLocation,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=16,
    )


class MediaAsset(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (Index("ix_media_assets_public", "status", "is_visible", "created_at"),)

    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    alt_text: Mapped[str] = mapped_column(String(300))
    is_decorative: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    caption: Mapped[str | None] = mapped_column(String(500))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    page_count: Mapped[int | None] = mapped_column(Integer)


class Article(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "articles"
    __table_args__ = (Index("ix_articles_public_date", "status", "is_visible", "published_at"),)

    hero_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(240))
    slug: Mapped[str] = mapped_column(String(260), unique=True, index=True)
    excerpt: Mapped[str] = mapped_column(Text)
    body_markdown: Mapped[str] = mapped_column(Text)
    topics: Mapped[list[str]] = mapped_column(json_type(), default=list)
    reading_minutes: Mapped[int | None] = mapped_column(Integer)
    seo_title: Mapped[str | None] = mapped_column(String(200))
    seo_description: Mapped[str | None] = mapped_column(String(320))

    hero_media: Mapped[MediaAsset | None] = relationship(lazy="joined")


class HomepageSection(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "homepage_sections"
    __table_args__ = (
        Index("uq_homepage_sections_position", "position", unique=True),
        Index("ix_homepage_sections_public_order", "status", "is_visible", "position"),
    )

    section_type: Mapped[HomepageSectionType] = mapped_column(homepage_section_type())
    title: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    variant: Mapped[str] = mapped_column(String(80), default="default", server_default="default")
    animation_variant: Mapped[str | None] = mapped_column(String(80))
    data_limit: Mapped[int | None] = mapped_column(Integer)
    show_cta: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    theme: Mapped[str | None] = mapped_column(String(80))
    feature_key: Mapped[str | None] = mapped_column(String(120), index=True)
    configuration: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict)


class NavigationItem(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "navigation_items"
    __table_args__ = (
        Index("ix_navigation_public_order", "location", "status", "is_visible", "sort_order"),
    )

    label: Mapped[str] = mapped_column(String(120))
    href: Mapped[str] = mapped_column(String(2048))
    location: Mapped[NavigationLocation] = mapped_column(
        navigation_location_type(),
        default=NavigationLocation.HEADER,
        server_default=NavigationLocation.HEADER.value,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    open_in_new_tab: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class FeatureSetting(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, Base):
    __tablename__ = "feature_settings"

    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    configuration: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
