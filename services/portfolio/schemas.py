from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import Field, HttpUrl, field_validator, model_validator

from packages.python.common.models import PublicationStatus
from packages.python.common.schemas import APIModel, EntityRead, PublicationRead
from services.portfolio.models import (
    EvidenceKind,
    EvidenceVisibility,
    ProjectNature,
    RepositorySnapshotStatus,
)

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_media_accessibility(
    media_type: str, alt_text: str, caption: str | None, is_decorative: bool
) -> None:
    alt = alt_text.strip()
    if is_decorative:
        if not media_type.startswith("image/"):
            raise ValueError("only images can be decorative")
        if alt:
            raise ValueError("decorative images must use empty alternative text")
        return
    if media_type.startswith("image/") and not alt:
        raise ValueError("informative images require meaningful alternative text")
    if not media_type.startswith("image/") and not (alt or (caption and caption.strip())):
        raise ValueError("documents and videos require an accessible label or caption")


class PublishableInput(APIModel):
    status: PublicationStatus = PublicationStatus.DRAFT
    is_visible: bool = True
    noindex: bool = False


class OrderedInput(APIModel):
    sort_order: int = Field(default=0, ge=0, le=100_000)


class SlugModel(APIModel):
    slug: str = Field(min_length=1, max_length=220)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _SLUG_PATTERN.fullmatch(normalized):
            raise ValueError("slug must contain lowercase letters, numbers, and single hyphens")
        return normalized


class CategoryCreate(SlugModel, PublishableInput, OrderedInput):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=5_000)
    color: str | None = Field(default=None, max_length=32)
    icon_key: str | None = Field(default=None, max_length=120)


class CategoryUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=140)
    description: str | None = Field(default=None, min_length=1, max_length=5_000)
    color: str | None = Field(default=None, max_length=32)
    icon_key: str | None = Field(default=None, max_length=120)
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    is_visible: bool | None = None
    noindex: bool | None = None

    _validate_slug = field_validator("slug")(
        lambda value: SlugModel.validate_slug(value) if value is not None else value
    )


class CategoryRead(EntityRead, PublicationRead):
    name: str
    slug: str
    description: str
    color: str | None
    icon_key: str | None
    sort_order: int


class SectorCreate(SlugModel, PublishableInput, OrderedInput):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=5_000)
    color: str | None = Field(default=None, max_length=32)
    icon_key: str | None = Field(default=None, max_length=120)


class SectorUpdate(CategoryUpdate):
    pass


class SectorRead(CategoryRead):
    project_count: int = Field(default=0, ge=0)


class SkillCreate(SlugModel, PublishableInput, OrderedInput):
    category_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5_000)
    icon_key: str | None = Field(default=None, max_length=120)
    proficiency_label: str | None = Field(default=None, max_length=80)
    years_experience: int | None = Field(default=None, ge=0, le=80)


class SkillUpdate(APIModel):
    category_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=140)
    description: str | None = Field(default=None, max_length=5_000)
    icon_key: str | None = Field(default=None, max_length=120)
    proficiency_label: str | None = Field(default=None, max_length=80)
    years_experience: int | None = Field(default=None, ge=0, le=80)
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    is_visible: bool | None = None
    noindex: bool | None = None

    _validate_slug = field_validator("slug")(
        lambda value: SlugModel.validate_slug(value) if value is not None else value
    )


class SkillSummary(APIModel):
    id: UUID
    name: str
    slug: str
    icon_key: str | None


class SkillRead(EntityRead, PublicationRead):
    category_id: UUID | None
    name: str
    slug: str
    description: str | None
    icon_key: str | None
    proficiency_label: str | None
    years_experience: int | None
    sort_order: int
    category: CategoryRead | None = None


class PublicSkillRead(APIModel):
    """Sanitized skill projection with no private taxonomy relationship identifier."""

    id: UUID
    updated_at: datetime
    published_at: datetime | None
    noindex: bool
    name: str
    slug: str
    description: str | None
    icon_key: str | None
    proficiency_label: str | None
    years_experience: int | None
    sort_order: int
    category: CategoryRead | None = None
    project_count: int = Field(default=0, ge=0)


class DatedInput(APIModel):
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> DatedInput:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot precede start_date")
        return self


class ExperienceCreate(DatedInput, PublishableInput, OrderedInput):
    organization: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=160)
    employment_type: str | None = Field(default=None, max_length=80)
    start_date: date
    summary: str = Field(min_length=1, max_length=20_000)
    achievements: list[str] = Field(default_factory=list, max_length=100)
    skill_ids: list[UUID] = Field(default_factory=list, max_length=200)
    sector_ids: list[UUID] = Field(default_factory=list, max_length=100)
    project_ids: list[UUID] = Field(default_factory=list, max_length=200)


class ExperienceUpdate(APIModel):
    organization: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=160)
    employment_type: str | None = Field(default=None, max_length=80)
    start_date: date | None = None
    end_date: date | None = None
    summary: str | None = Field(default=None, min_length=1, max_length=20_000)
    achievements: list[str] | None = Field(default=None, max_length=100)
    skill_ids: list[UUID] | None = Field(default=None, max_length=200)
    sector_ids: list[UUID] | None = Field(default=None, max_length=100)
    project_ids: list[UUID] | None = Field(default=None, max_length=200)
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    is_visible: bool | None = None
    noindex: bool | None = None


class ProjectSummary(APIModel):
    id: UUID
    title: str
    slug: str
    summary: str
    featured_rank: int | None


class ExperienceRead(EntityRead, PublicationRead):
    organization: str
    role: str
    location: str | None
    employment_type: str | None
    start_date: date
    end_date: date | None
    summary: str
    achievements: list[str]
    sort_order: int
    skills: list[SkillSummary] = Field(default_factory=list)
    sectors: list[SectorRead] = Field(default_factory=list)
    projects: list[ProjectSummary] = Field(default_factory=list)


class EducationCreate(DatedInput, PublishableInput, OrderedInput):
    institution: str = Field(min_length=1, max_length=200)
    credential: str = Field(min_length=1, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=160)
    summary: str | None = Field(default=None, max_length=20_000)
    achievements: list[str] = Field(default_factory=list, max_length=100)


class EducationUpdate(APIModel):
    institution: str | None = Field(default=None, min_length=1, max_length=200)
    credential: str | None = Field(default=None, min_length=1, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=160)
    start_date: date | None = None
    end_date: date | None = None
    summary: str | None = Field(default=None, max_length=20_000)
    achievements: list[str] | None = Field(default=None, max_length=100)
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    is_visible: bool | None = None
    noindex: bool | None = None


class EducationRead(EntityRead, PublicationRead):
    institution: str
    credential: str
    field_of_study: str | None
    location: str | None
    start_date: date | None
    end_date: date | None
    summary: str | None
    achievements: list[str]
    sort_order: int


class CertificationCreate(PublishableInput, OrderedInput):
    name: str = Field(min_length=1, max_length=240)
    issuer: str = Field(min_length=1, max_length=200)
    credential_id: str | None = Field(default=None, max_length=200)
    credential_url: HttpUrl | None = None
    issued_on: date | None = None
    expires_on: date | None = None
    description: str | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def validate_dates(self) -> CertificationCreate:
        if self.issued_on and self.expires_on and self.expires_on < self.issued_on:
            raise ValueError("expires_on cannot precede issued_on")
        return self


class CertificationUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=240)
    issuer: str | None = Field(default=None, min_length=1, max_length=200)
    credential_id: str | None = Field(default=None, max_length=200)
    credential_url: HttpUrl | None = None
    issued_on: date | None = None
    expires_on: date | None = None
    description: str | None = Field(default=None, max_length=10_000)
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    is_visible: bool | None = None
    noindex: bool | None = None


class CertificationRead(EntityRead, PublicationRead):
    name: str
    issuer: str
    credential_id: str | None
    credential_url: str | None
    issued_on: date | None
    expires_on: date | None
    description: str | None
    sort_order: int


class ProjectLink(APIModel):
    label: str = Field(min_length=1, max_length=80)
    url: HttpUrl


class ProjectCreate(DatedInput, SlugModel, PublishableInput):
    category_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2_000)
    description: str | None = Field(default=None, max_length=50_000)
    role: str | None = Field(default=None, max_length=200)
    problem: str | None = Field(default=None, max_length=30_000)
    solution: str | None = Field(default=None, max_length=30_000)
    architecture: str | None = Field(default=None, max_length=30_000)
    features: list[str] = Field(default_factory=list, max_length=200)
    decisions: list[str] = Field(default_factory=list, max_length=200)
    tradeoffs: list[str] = Field(default_factory=list, max_length=200)
    challenges: list[str] = Field(default_factory=list, max_length=200)
    outcomes: list[str] = Field(default_factory=list, max_length=200)
    links: list[ProjectLink] = Field(default_factory=list, max_length=30)
    repository_url: HttpUrl | None = None
    live_url: HttpUrl | None = None
    is_open_source: bool = False
    repository_metadata_refresh_enabled: bool = False
    nature: ProjectNature | None = None
    featured_rank: int | None = Field(default=None, ge=1, le=5)
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    skill_ids: list[UUID] = Field(default_factory=list, max_length=200)
    sector_ids: list[UUID] = Field(default_factory=list, max_length=100)


class ProjectUpdate(APIModel):
    category_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    summary: str | None = Field(default=None, min_length=1, max_length=2_000)
    description: str | None = Field(default=None, max_length=50_000)
    role: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    problem: str | None = Field(default=None, max_length=30_000)
    solution: str | None = Field(default=None, max_length=30_000)
    architecture: str | None = Field(default=None, max_length=30_000)
    features: list[str] | None = Field(default=None, max_length=200)
    decisions: list[str] | None = Field(default=None, max_length=200)
    tradeoffs: list[str] | None = Field(default=None, max_length=200)
    challenges: list[str] | None = Field(default=None, max_length=200)
    outcomes: list[str] | None = Field(default=None, max_length=200)
    links: list[ProjectLink] | None = Field(default=None, max_length=30)
    repository_url: HttpUrl | None = None
    live_url: HttpUrl | None = None
    is_open_source: bool | None = None
    repository_metadata_refresh_enabled: bool | None = None
    nature: ProjectNature | None = None
    featured_rank: int | None = Field(default=None, ge=1, le=5)
    seo_title: str | None = Field(default=None, max_length=200)
    seo_description: str | None = Field(default=None, max_length=320)
    skill_ids: list[UUID] | None = Field(default=None, max_length=200)
    sector_ids: list[UUID] | None = Field(default=None, max_length=100)
    is_visible: bool | None = None
    noindex: bool | None = None

    _validate_slug = field_validator("slug")(
        lambda value: SlugModel.validate_slug(value) if value is not None else value
    )


class FeaturedProjectOrderUpdate(APIModel):
    project_ids: list[UUID] = Field(min_length=0, max_length=5)

    @field_validator("project_ids")
    @classmethod
    def validate_unique_projects(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("featured projects cannot contain duplicates")
        return value


class ProjectMediaCreate(APIModel):
    project_id: UUID
    external_url: HttpUrl
    media_type: str = Field(min_length=1, max_length=100)
    alt_text: str = Field(default="", max_length=300)
    is_decorative: bool = False
    caption: str | None = Field(default=None, max_length=500)
    width: int | None = Field(default=None, ge=1, le=50_000)
    height: int | None = Field(default=None, ge=1, le=50_000)
    duration_seconds: int | None = Field(default=None, ge=0, le=604_800)
    sort_order: int = Field(default=0, ge=0, le=100_000)
    is_visible: bool = True

    @model_validator(mode="after")
    def validate_accessibility(self) -> ProjectMediaCreate:
        _validate_media_accessibility(
            self.media_type, self.alt_text, self.caption, self.is_decorative
        )
        return self


class ProjectMediaUploadMetadata(APIModel):
    project_id: UUID
    alt_text: str = Field(default="", max_length=300)
    is_decorative: bool = False
    caption: str | None = Field(default=None, max_length=500)
    width: int | None = Field(default=None, ge=1, le=50_000)
    height: int | None = Field(default=None, ge=1, le=50_000)
    duration_seconds: int | None = Field(default=None, ge=0, le=604_800)
    sort_order: int = Field(default=0, ge=0, le=100_000)
    is_visible: bool = True

    @model_validator(mode="after")
    def validate_decorative_alt(self) -> ProjectMediaUploadMetadata:
        if self.is_decorative and self.alt_text.strip():
            raise ValueError("decorative images must use empty alternative text")
        return self


class ProjectMediaUpdate(APIModel):
    project_id: UUID | None = None
    external_url: HttpUrl | None = None
    media_type: str | None = Field(default=None, min_length=1, max_length=100)
    alt_text: str | None = Field(default=None, max_length=300)
    is_decorative: bool | None = None
    caption: str | None = Field(default=None, max_length=500)
    width: int | None = Field(default=None, ge=1, le=50_000)
    height: int | None = Field(default=None, ge=1, le=50_000)
    duration_seconds: int | None = Field(default=None, ge=0, le=604_800)
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    is_visible: bool | None = None


class ProjectMediaRead(EntityRead):
    project_id: UUID
    external_url: str | None
    original_filename: str | None
    media_type: str
    size_bytes: int | None
    sha256: str | None
    alt_text: str
    is_decorative: bool
    caption: str | None
    width: int | None
    height: int | None
    duration_seconds: int | None
    page_count: int | None
    sort_order: int
    is_visible: bool


class EvidenceInput(APIModel):
    kind: EvidenceKind
    visibility: EvidenceVisibility = EvidenceVisibility.PRIVATE_REVIEW
    reference_url: HttpUrl | None = None
    managed_media_id: UUID | None = None
    reference_text: str | None = Field(default=None, min_length=12, max_length=2048)
    public_label: str | None = Field(default=None, min_length=3, max_length=160)
    provenance: str = Field(min_length=3, max_length=500)
    captured_at: date
    reviewer_note: str | None = Field(default=None, max_length=5_000)

    @model_validator(mode="after")
    def validate_locator_and_visibility(self) -> EvidenceInput:
        populated = sum(
            value is not None
            for value in (self.reference_url, self.managed_media_id, self.reference_text)
        )
        if populated != 1:
            raise ValueError("evidence must contain exactly one source locator")
        expected = {
            EvidenceKind.PUBLIC_URL: self.reference_url,
            EvidenceKind.MANAGED_MEDIA: self.managed_media_id,
            EvidenceKind.DOCUMENT_REFERENCE: self.reference_text,
        }[self.kind]
        if expected is None:
            raise ValueError("evidence source does not match its kind")
        if self.reference_url is not None:
            if self.reference_url.scheme != "https":
                raise ValueError("evidence URLs must use https")
            if self.reference_url.username or self.reference_url.password:
                raise ValueError("evidence URLs must not contain credentials")
        if self.visibility is EvidenceVisibility.PUBLIC and not self.public_label:
            raise ValueError("public evidence requires a public label")
        return self


class EvidenceRead(EntityRead):
    kind: EvidenceKind
    visibility: EvidenceVisibility
    reference_url: str | None
    managed_media_id: UUID | None
    reference_text: str | None
    public_label: str | None
    provenance: str
    captured_at: date
    reviewer_note: str | None
    revision: int
    archived_at: datetime | None
    managed_media: ProjectMediaRead | None = None


class PublicEvidenceRead(APIModel):
    label: str
    url: str | None = None
    captured_at: date


class MetricCreate(PublishableInput, OrderedInput):
    project_id: UUID | None = None
    experience_id: UUID | None = None
    subject_label: str | None = Field(default=None, max_length=200)
    label: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=100)
    unit: str | None = Field(default=None, max_length=80)
    context: str = Field(min_length=1, max_length=5_000)
    evidence: EvidenceInput | None = None


class MetricUpdate(APIModel):
    project_id: UUID | None = None
    experience_id: UUID | None = None
    subject_label: str | None = Field(default=None, max_length=200)
    label: str | None = Field(default=None, min_length=1, max_length=160)
    value: str | None = Field(default=None, min_length=1, max_length=100)
    unit: str | None = Field(default=None, max_length=80)
    context: str | None = Field(default=None, min_length=1, max_length=5_000)
    evidence: EvidenceInput | None = None
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    is_visible: bool | None = None
    noindex: bool | None = None


class MetricRead(EntityRead, PublicationRead):
    project_id: UUID | None
    experience_id: UUID | None
    subject_label: str | None
    label: str
    value: str
    unit: str | None
    context: str
    evidence: EvidenceRead | None
    is_approved: bool
    approved_at: datetime | None
    approved_by_admin_id: UUID | None
    approved_revision_hash: str | None
    created_by_admin_id: UUID | None
    sort_order: int


class PublicMetricRead(EntityRead, PublicationRead):
    project_id: UUID | None
    experience_id: UUID | None
    subject_label: str | None
    label: str
    value: str
    unit: str | None
    context: str
    public_evidence: PublicEvidenceRead | None = None
    sort_order: int


class TestimonialCreate(PublishableInput, OrderedInput):
    project_id: UUID | None = None
    experience_id: UUID | None = None
    subject_label: str | None = Field(default=None, max_length=200)
    quote: str = Field(min_length=1, max_length=10_000)
    attribution_name: str = Field(min_length=1, max_length=160)
    attribution_title: str | None = Field(default=None, max_length=160)
    attribution_organization: str | None = Field(default=None, max_length=200)
    evidence: EvidenceInput | None = None


class TestimonialUpdate(APIModel):
    project_id: UUID | None = None
    experience_id: UUID | None = None
    subject_label: str | None = Field(default=None, max_length=200)
    quote: str | None = Field(default=None, min_length=1, max_length=10_000)
    attribution_name: str | None = Field(default=None, min_length=1, max_length=160)
    attribution_title: str | None = Field(default=None, max_length=160)
    attribution_organization: str | None = Field(default=None, max_length=200)
    evidence: EvidenceInput | None = None
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    is_visible: bool | None = None
    noindex: bool | None = None


class TestimonialRead(EntityRead, PublicationRead):
    project_id: UUID | None
    experience_id: UUID | None
    subject_label: str | None
    quote: str
    attribution_name: str
    attribution_title: str | None
    attribution_organization: str | None
    evidence: EvidenceRead | None
    is_approved: bool
    approved_at: datetime | None
    approved_by_admin_id: UUID | None
    approved_revision_hash: str | None
    created_by_admin_id: UUID | None
    sort_order: int


class PublicTestimonialRead(EntityRead, PublicationRead):
    project_id: UUID | None
    experience_id: UUID | None
    subject_label: str | None
    quote: str
    attribution_name: str
    attribution_title: str | None
    attribution_organization: str | None
    public_evidence: PublicEvidenceRead | None = None
    sort_order: int


class RepositoryMetadataAdminRead(EntityRead):
    provider: str
    repository_identity: str | None
    language: str | None
    stars: int | None
    forks: int | None
    fetched_at: datetime | None
    stale_after: datetime | None
    status: RepositorySnapshotStatus
    last_error_code: str | None
    last_error_at: datetime | None
    retry_after: datetime | None


class PublicRepositoryMetadataRead(APIModel):
    provider: str
    repository_identity: str
    language: str | None
    stars: int | None
    forks: int | None
    fetched_at: datetime
    freshness: str


class ProjectRead(EntityRead, PublicationRead):
    category_id: UUID | None
    title: str
    slug: str
    summary: str
    description: str | None
    role: str | None
    start_date: date | None
    end_date: date | None
    problem: str | None
    solution: str | None
    architecture: str | None
    features: list[str]
    decisions: list[str]
    tradeoffs: list[str]
    challenges: list[str]
    outcomes: list[str]
    links: list[dict[str, Any]]
    repository_url: str | None
    live_url: str | None
    is_open_source: bool
    repository_metadata_refresh_enabled: bool
    nature: ProjectNature
    featured_rank: int | None
    seo_title: str | None
    seo_description: str | None
    category: CategoryRead | None = None
    skills: list[SkillSummary] = Field(default_factory=list)
    sectors: list[SectorRead] = Field(default_factory=list)
    media: list[ProjectMediaRead] = Field(default_factory=list)
    metrics: list[MetricRead] = Field(default_factory=list)
    testimonials: list[TestimonialRead] = Field(default_factory=list)
    repository_metadata: RepositoryMetadataAdminRead | None = None


class PublicProjectSummaryRead(EntityRead, PublicationRead):
    """Bounded project-card projection with no long-form narrative or testimonials."""

    title: str
    slug: str
    summary: str
    role: str | None
    start_date: date | None
    end_date: date | None
    links: list[dict[str, Any]]
    repository_url: str | None
    live_url: str | None
    is_open_source: bool
    nature: ProjectNature
    repository_metadata: PublicRepositoryMetadataRead | None = None
    featured_rank: int | None
    seo_title: str | None
    seo_description: str | None
    category: CategoryRead | None = None
    skills: list[SkillSummary] = Field(default_factory=list)
    sectors: list[SectorRead] = Field(default_factory=list)
    media: list[ProjectMediaRead] = Field(default_factory=list)
    metrics: list[PublicMetricRead] = Field(default_factory=list)


class PublicProjectRead(PublicProjectSummaryRead):
    """Sanitized detail with each canonical narrative field represented once."""

    description: str | None
    problem: str | None
    solution: str | None
    architecture: str | None
    features: list[str]
    decisions: list[str]
    tradeoffs: list[str]
    challenges: list[str]
    outcomes: list[str]
    testimonials: list[PublicTestimonialRead] = Field(default_factory=list)
    related_projects: list[PublicProjectSummaryRead] = Field(default_factory=list)


class FeaturedProjectOrderRead(APIModel):
    limit: int = Field(ge=1, le=5)
    projects: list[ProjectRead]


class PublicSectorDetailRead(APIModel):
    sector: SectorRead
    projects: list[PublicProjectSummaryRead]
    total: int = Field(ge=0)
