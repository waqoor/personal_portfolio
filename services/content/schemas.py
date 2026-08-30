from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from packages.python.common.models import PublicationStatus
from packages.python.common.schemas import APIModel, EntityRead, PublicationRead
from services.content.models import HomepageSectionType, NavigationLocation
from services.identity.schemas import ProfileRead, PublicResumeRead

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FEATURE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{1,119}$")
_MOTION_VARIANTS = frozenset({"none", "reveal", "stagger"})
_SENSITIVE_CONFIGURATION_KEY = re.compile(
    r"(?:^|[._-])(password|secret|token|api[._-]?key|private[._-]?key|credential|authorization)"
    r"(?:$|[._-])",
    re.IGNORECASE,
)
_MAX_CONFIGURATION_BYTES = 32 * 1024
_MAX_CONFIGURATION_DEPTH = 8
_MAX_CONFIGURATION_ITEMS = 500
_LEGACY_SITE_PRESENTATION_KEYS = frozenset({"analytics_enabled", "site_url", "timezone"})


def validate_public_configuration(value: dict[str, Any]) -> dict[str, Any]:
    """Bound public configuration and reject values that resemble credentials."""

    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("configuration must contain JSON-compatible values") from exc
    if len(encoded) > _MAX_CONFIGURATION_BYTES:
        raise ValueError("configuration exceeds the 32 KiB limit")

    item_count = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > _MAX_CONFIGURATION_DEPTH:
            raise ValueError("configuration nesting is too deep")
        if isinstance(current, dict):
            item_count += len(current)
            for key, nested in current.items():
                if _SENSITIVE_CONFIGURATION_KEY.search(key):
                    raise ValueError("configuration cannot contain credential-like keys")
                stack.append((nested, depth + 1))
        elif isinstance(current, list):
            item_count += len(current)
            stack.extend((nested, depth + 1) for nested in current)
        elif isinstance(current, str) and len(current) > 8_192:
            raise ValueError("configuration string values cannot exceed 8192 characters")
        if item_count > _MAX_CONFIGURATION_ITEMS:
            raise ValueError("configuration contains too many items")
    return value


class MediaRead(EntityRead, PublicationRead):
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    alt_text: str
    is_decorative: bool
    caption: str | None
    width: int | None
    height: int | None
    duration_seconds: int | None
    page_count: int | None


class MediaUploadMetadata(APIModel):
    alt_text: str = Field(default="", max_length=300)
    is_decorative: bool = False
    caption: str | None = Field(default=None, max_length=500)
    width: int | None = Field(default=None, ge=1, le=50_000)
    height: int | None = Field(default=None, ge=1, le=50_000)
    duration_seconds: int | None = Field(default=None, ge=0, le=604_800)

    @model_validator(mode="after")
    def validate_accessible_name(self) -> MediaUploadMetadata:
        if self.is_decorative and self.alt_text.strip():
            raise ValueError("decorative media must use empty alternative text")
        if not self.is_decorative and not (self.alt_text.strip() or self.caption):
            raise ValueError("informative media requires alternative text or a caption")
        return self


class MediaUpdate(APIModel):
    alt_text: str | None = Field(default=None, max_length=300)
    is_decorative: bool | None = None
    caption: str | None = Field(default=None, max_length=500)
    width: int | None = Field(default=None, ge=1, le=50_000)
    height: int | None = Field(default=None, ge=1, le=50_000)
    duration_seconds: int | None = Field(default=None, ge=0, le=604_800)
    is_visible: bool | None = None
    noindex: bool | None = None


class ArticleCreate(APIModel):
    hero_media_id: UUID | None = None
    title: str = Field(min_length=1, max_length=240)
    slug: str = Field(min_length=1, max_length=260)
    excerpt: str = Field(min_length=1, max_length=2_000)
    body_markdown: str = Field(min_length=1, max_length=200_000)
    topics: list[str] = Field(default_factory=list, max_length=50)
    reading_minutes: int | None = Field(default=None, ge=1, le=10_000)
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    status: PublicationStatus = PublicationStatus.DRAFT
    is_visible: bool = True
    noindex: bool = False

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        normalized = value.lower()
        if not _SLUG_PATTERN.fullmatch(normalized):
            raise ValueError("slug must contain lowercase letters, numbers, and single hyphens")
        return normalized


class ArticleUpdate(APIModel):
    hero_media_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    slug: str | None = Field(default=None, min_length=1, max_length=260)
    excerpt: str | None = Field(default=None, min_length=1, max_length=2_000)
    body_markdown: str | None = Field(default=None, min_length=1, max_length=200_000)
    topics: list[str] | None = Field(default=None, max_length=50)
    reading_minutes: int | None = Field(default=None, ge=1, le=10_000)
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    is_visible: bool | None = None
    noindex: bool | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        return ArticleCreate.validate_slug(value) if value is not None else None


class ArticleRead(EntityRead, PublicationRead):
    hero_media_id: UUID | None
    title: str
    slug: str
    excerpt: str
    body_markdown: str
    topics: list[str]
    reading_minutes: int | None
    seo_title: str | None
    seo_description: str | None
    hero_media: MediaRead | None = None


class PublicArticleSummaryRead(EntityRead, PublicationRead):
    """Bounded article-card projection; intentionally excludes body_markdown."""

    title: str
    slug: str
    excerpt: str
    topics: list[str]
    reading_minutes: int | None
    seo_title: str | None
    seo_description: str | None
    hero_media: MediaRead | None = None


class PublicArticleRead(PublicArticleSummaryRead):
    body_markdown: str
    related_articles: list[PublicArticleSummaryRead] = Field(default_factory=list)


class ArticlePage(APIModel):
    items: list[PublicArticleSummaryRead]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    topics: list[str]


class HomepageSectionCreate(APIModel):
    section_type: HomepageSectionType
    title: str | None = Field(default=None, max_length=200)
    position: int = Field(ge=0, le=10_000)
    enabled: bool = True
    variant: str | None = Field(default=None, min_length=1, max_length=80)
    animation_variant: str | None = Field(default=None, max_length=80)
    data_limit: int | None = Field(default=None, ge=1, le=500)
    show_cta: bool = True
    theme: str | None = Field(default=None, max_length=80)
    feature_key: str | None = Field(default=None, max_length=120)
    configuration: dict[str, Any] = Field(default_factory=dict)
    status: PublicationStatus = PublicationStatus.DRAFT
    is_visible: bool = True
    noindex: bool = False

    @field_validator("feature_key")
    @classmethod
    def validate_feature_key(cls, value: str | None) -> str | None:
        if value is not None and not _FEATURE_KEY_PATTERN.fullmatch(value):
            raise ValueError("feature_key has an invalid format")
        return value

    @field_validator("animation_variant")
    @classmethod
    def validate_animation_variant(cls, value: str | None) -> str | None:
        if value is not None and value not in _MOTION_VARIANTS:
            raise ValueError("animation_variant is not supported")
        return value

    _validate_configuration = field_validator("configuration")(validate_public_configuration)


class HomepageSectionUpdate(APIModel):
    section_type: HomepageSectionType | None = None
    title: str | None = Field(default=None, max_length=200)
    position: int | None = Field(default=None, ge=0, le=10_000)
    enabled: bool | None = None
    variant: str | None = Field(default=None, min_length=1, max_length=80)
    animation_variant: str | None = Field(default=None, max_length=80)
    data_limit: int | None = Field(default=None, ge=1, le=500)
    show_cta: bool | None = None
    theme: str | None = Field(default=None, max_length=80)
    feature_key: str | None = Field(default=None, max_length=120)
    configuration: dict[str, Any] | None = None
    is_visible: bool | None = None
    noindex: bool | None = None

    _validate_feature_key = field_validator("feature_key")(
        HomepageSectionCreate.validate_feature_key
    )
    _validate_animation_variant = field_validator("animation_variant")(
        HomepageSectionCreate.validate_animation_variant
    )
    _validate_configuration = field_validator("configuration")(
        lambda value: validate_public_configuration(value) if value is not None else None
    )


class HomepageSectionCompositionItem(HomepageSectionCreate):
    """One ordered entry in the canonical homepage composition."""

    id: UUID | None = None


class HomepageCompositionUpdate(APIModel):
    sections: list[HomepageSectionCompositionItem] = Field(max_length=20)


class HomepageSectionRead(EntityRead, PublicationRead):
    section_type: HomepageSectionType
    title: str | None
    position: int
    enabled: bool
    variant: str
    animation_variant: str | None
    data_limit: int | None
    show_cta: bool
    theme: str | None
    feature_key: str | None
    configuration: dict[str, Any]


class NavigationItemCreate(APIModel):
    label: str = Field(min_length=1, max_length=120)
    href: str = Field(min_length=1, max_length=2048)
    location: NavigationLocation = NavigationLocation.HEADER
    sort_order: int = Field(default=0, ge=0, le=100_000)
    open_in_new_tab: bool = False
    status: PublicationStatus = PublicationStatus.DRAFT
    is_visible: bool = True
    noindex: bool = False

    @field_validator("href")
    @classmethod
    def validate_href(cls, value: str) -> str:
        if value.startswith("/") and not value.startswith("//"):
            return value
        parsed = urlparse(value)
        if parsed.username or parsed.password:
            raise ValueError("href cannot contain embedded credentials")
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return value
        if parsed.scheme == "mailto" and parsed.path and "@" in parsed.path:
            return value
        raise ValueError("href must be a relative path or an http(s)/mailto URL")


class NavigationItemUpdate(APIModel):
    label: str | None = Field(default=None, min_length=1, max_length=120)
    href: str | None = Field(default=None, min_length=1, max_length=2048)
    location: NavigationLocation | None = None
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    open_in_new_tab: bool | None = None
    is_visible: bool | None = None
    noindex: bool | None = None

    @field_validator("href")
    @classmethod
    def validate_href(cls, value: str | None) -> str | None:
        return NavigationItemCreate.validate_href(value) if value is not None else None


class NavigationItemRead(EntityRead, PublicationRead):
    label: str
    href: str
    location: NavigationLocation
    sort_order: int
    open_in_new_tab: bool


class SitePresentationSettings(APIModel):
    """Typed, public-safe presentation copy owned by the content domain."""

    site_name: str = Field(default="Portfolio", min_length=1, max_length=160)
    default_title: str = Field(default="Portfolio", min_length=1, max_length=200)
    default_description: str = Field(
        default="Selected work, experience, technical writing, and ways to collaborate.",
        min_length=1,
        max_length=320,
    )
    locale: str = Field(default="en", min_length=2, max_length=35)
    footer_eyebrow: str = Field(default="End of transmission", min_length=1, max_length=120)
    footer_heading: str = Field(default="Build what matters.", min_length=1, max_length=240)
    footer_statement: str = Field(
        default="Designed for people. Legible to machines.", min_length=1, max_length=240
    )
    about_title: str = Field(
        default="A builder working across systems and product.", min_length=1, max_length=240
    )
    about_intro: str = Field(
        default="Published experience, education, and verified credentials.",
        min_length=1,
        max_length=500,
    )
    achievements_title: str = Field(default="Achievements", min_length=1, max_length=200)
    achievements_intro: str = Field(
        default="Certifications, recognition, professional milestones, and published research.",
        min_length=1,
        max_length=500,
    )
    work_title: str = Field(default="Work", min_length=1, max_length=200)
    work_intro: str = Field(
        default="Full-time, contract, part-time, freelance, and project-based experience.",
        min_length=1,
        max_length=500,
    )
    projects_title: str = Field(default="Projects", min_length=1, max_length=200)
    projects_intro: str = Field(
        default="Case studies with decisions, constraints, and evidence.",
        min_length=1,
        max_length=500,
    )
    writing_title: str = Field(default="Writing", min_length=1, max_length=200)
    writing_intro: str = Field(
        default="Technical field notes and practical explanations.",
        min_length=1,
        max_length=500,
    )
    sectors_title: str = Field(default="Sectors", min_length=1, max_length=200)
    sectors_intro: str = Field(
        default="Applied domains supported by published project evidence.",
        min_length=1,
        max_length=500,
    )
    open_source_title: str = Field(default="Open source", min_length=1, max_length=200)
    open_source_intro: str = Field(
        default="Public repositories and contribution work.", min_length=1, max_length=500
    )
    sponsorship_title: str = Field(
        default="Support sustainable open-source work", min_length=1, max_length=200
    )
    sponsorship_description: str = Field(
        default="Transparent sponsorship helps maintain public technical work.",
        min_length=1,
        max_length=500,
    )
    sponsorship_principles: list[str] = Field(
        default_factory=lambda: [
            "Public work remains technically independent.",
            "Sponsored links are explicitly identified.",
            "No private access or endorsement is implied.",
        ],
        min_length=1,
        max_length=8,
    )

    @field_validator("sponsorship_principles")
    @classmethod
    def validate_principles(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 240 for value in normalized):
            raise ValueError("sponsorship principles must contain 1 to 240 characters")
        return normalized

    @classmethod
    def from_persisted_configuration(
        cls, configuration: Mapping[str, Any]
    ) -> SitePresentationSettings:
        """Project known legacy platform keys out of stored presentation settings.

        Early installations stored deployment/runtime fields in the same JSON object.
        Those values remain preserved in PostgreSQL, but they are not presentation
        fields and must not make current public reads fail after an application upgrade.
        Unexpected non-legacy keys still fail strict validation so configuration drift
        is not silently hidden.
        """

        presentation = {
            key: value
            for key, value in configuration.items()
            if key not in _LEGACY_SITE_PRESENTATION_KEYS
        }
        return cls.model_validate(presentation)


class FeatureSettingUpsert(APIModel):
    key: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool = True
    configuration: dict[str, Any] = Field(default_factory=dict)

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        if not _FEATURE_KEY_PATTERN.fullmatch(value):
            raise ValueError("feature key has an invalid format")
        return value

    _validate_configuration = field_validator("configuration")(validate_public_configuration)

    @model_validator(mode="after")
    def validate_typed_configuration(self) -> FeatureSettingUpsert:
        if self.key == "site_settings":
            self.configuration = SitePresentationSettings.model_validate(
                self.configuration
            ).model_dump(mode="json")
        return self


class FeatureSettingRead(EntityRead):
    key: str
    description: str | None
    enabled: bool
    configuration: dict[str, Any]
    archived_at: datetime | None


class HomepageSectionPayload(APIModel):
    section: HomepageSectionRead
    data: Any = None


class HomepageRead(APIModel):
    profile: ProfileRead | None
    current_resume: PublicResumeRead | None
    navigation: list[NavigationItemRead]
    features: dict[str, bool]
    feature_configurations: dict[str, dict[str, Any]]
    site_presentation: SitePresentationSettings
    sections: list[HomepageSectionPayload]


class PublicSiteShellRead(APIModel):
    """Small global-chrome projection; deliberately excludes homepage section payloads."""

    profile: ProfileRead | None
    navigation: list[NavigationItemRead]
    features: dict[str, bool]
    feature_configurations: dict[str, dict[str, Any]]
    site_presentation: SitePresentationSettings
