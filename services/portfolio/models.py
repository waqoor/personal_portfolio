from __future__ import annotations

import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    text,
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


class EvidenceKind(enum.StrEnum):
    PUBLIC_URL = "public_url"
    MANAGED_MEDIA = "managed_media"
    DOCUMENT_REFERENCE = "document_reference"


class EvidenceVisibility(enum.StrEnum):
    PRIVATE_REVIEW = "private_review"
    PUBLIC = "public"


class ApprovalAction(enum.StrEnum):
    APPROVED = "approved"
    REVOKED = "revoked"
    AUTO_REVOKED = "auto_revoked"


class ProjectNature(enum.StrEnum):
    CASE_STUDY = "case_study"
    PRODUCT = "product"
    SOFTWARE = "software"


class RepositorySnapshotStatus(enum.StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    REFRESHING = "refreshing"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"


def _string_enum(enum_type: type[enum.StrEnum], *, length: int) -> Enum:
    return Enum(
        enum_type,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=length,
    )


project_skills = Table(
    "project_skills",
    Base.metadata,
    Column("project_id", Uuid, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", Uuid, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)

project_sectors = Table(
    "project_sectors",
    Base.metadata,
    Column("project_id", Uuid, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("sector_id", Uuid, ForeignKey("sectors.id", ondelete="CASCADE"), primary_key=True),
)

experience_skills = Table(
    "experience_skills",
    Base.metadata,
    Column(
        "experience_id", Uuid, ForeignKey("experiences.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("skill_id", Uuid, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)

experience_sectors = Table(
    "experience_sectors",
    Base.metadata,
    Column(
        "experience_id", Uuid, ForeignKey("experiences.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("sector_id", Uuid, ForeignKey("sectors.id", ondelete="CASCADE"), primary_key=True),
)

experience_projects = Table(
    "experience_projects",
    Base.metadata,
    Column(
        "experience_id", Uuid, ForeignKey("experiences.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("project_id", Uuid, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
)


class ProfessionalCategory(
    UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base
):
    __tablename__ = "professional_categories"
    __table_args__ = (Index("ix_categories_public_order", "status", "is_visible", "sort_order"),)

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(32))
    icon_key: Mapped[str | None] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    skills: Mapped[list[Skill]] = relationship(back_populates="category", lazy="selectin")
    projects: Mapped[list[Project]] = relationship(back_populates="category", lazy="selectin")


class Sector(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "sectors"
    __table_args__ = (Index("ix_sectors_public_order", "status", "is_visible", "sort_order"),)

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(32))
    icon_key: Mapped[str | None] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    projects: Mapped[list[Project]] = relationship(
        secondary=project_sectors, back_populates="sectors", lazy="selectin"
    )
    experiences: Mapped[list[Experience]] = relationship(
        secondary=experience_sectors, back_populates="sectors", lazy="selectin"
    )


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (Index("ix_skills_public_order", "status", "is_visible", "sort_order"),)

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("professional_categories.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    icon_key: Mapped[str | None] = mapped_column(String(120))
    proficiency_label: Mapped[str | None] = mapped_column(String(80))
    years_experience: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    category: Mapped[ProfessionalCategory | None] = relationship(
        back_populates="skills", lazy="joined"
    )
    projects: Mapped[list[Project]] = relationship(
        secondary=project_skills, back_populates="skills", lazy="selectin"
    )
    experiences: Mapped[list[Experience]] = relationship(
        secondary=experience_skills, back_populates="skills", lazy="selectin"
    )


class Experience(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "experiences"
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_experience_dates"),
        Index("ix_experiences_public_dates", "status", "is_visible", "start_date"),
    )

    organization: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(160))
    employment_type: Mapped[str | None] = mapped_column(String(80))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    summary: Mapped[str] = mapped_column(Text)
    achievements: Mapped[list[str]] = mapped_column(json_type(), default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    skills: Mapped[list[Skill]] = relationship(
        secondary=experience_skills, back_populates="experiences", lazy="selectin"
    )
    sectors: Mapped[list[Sector]] = relationship(
        secondary=experience_sectors, back_populates="experiences", lazy="selectin"
    )
    projects: Mapped[list[Project]] = relationship(
        secondary=experience_projects, back_populates="experiences", lazy="selectin"
    )


class Education(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "education"
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_education_dates"),
        Index("ix_education_public_dates", "status", "is_visible", "start_date"),
    )

    institution: Mapped[str] = mapped_column(String(200))
    credential: Mapped[str] = mapped_column(String(200))
    field_of_study: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(160))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)
    achievements: Mapped[list[str]] = mapped_column(json_type(), default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Certification(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "certifications"
    __table_args__ = (
        CheckConstraint(
            "expires_on IS NULL OR issued_on IS NULL OR expires_on >= issued_on",
            name="ck_certification_dates",
        ),
        Index("ix_certifications_public_order", "status", "is_visible", "sort_order"),
    )

    name: Mapped[str] = mapped_column(String(240))
    issuer: Mapped[str] = mapped_column(String(200))
    credential_id: Mapped[str | None] = mapped_column(String(200))
    credential_url: Mapped[str | None] = mapped_column(String(2048))
    issued_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Project(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_project_dates",
        ),
        CheckConstraint(
            "featured_rank IS NULL OR featured_rank > 0",
            name="ck_project_featured_rank",
        ),
        Index("ix_projects_public_featured", "status", "is_visible", "featured_rank"),
        Index(
            "uq_projects_active_featured_rank",
            "featured_rank",
            unique=True,
            postgresql_where=text(
                "featured_rank IS NOT NULL AND status = 'published' AND is_visible = true "
                "AND archived_at IS NULL"
            ),
            sqlite_where=text(
                "featured_rank IS NOT NULL AND status = 'published' AND is_visible = 1 "
                "AND archived_at IS NULL"
            ),
        ),
        Index("ix_projects_public_date", "status", "is_visible", "start_date"),
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("professional_categories.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    summary: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    problem: Mapped[str | None] = mapped_column(Text)
    solution: Mapped[str | None] = mapped_column(Text)
    architecture: Mapped[str | None] = mapped_column(Text)
    features: Mapped[list[str]] = mapped_column(json_type(), default=list)
    decisions: Mapped[list[str]] = mapped_column(json_type(), default=list)
    tradeoffs: Mapped[list[str]] = mapped_column(json_type(), default=list)
    challenges: Mapped[list[str]] = mapped_column(json_type(), default=list)
    outcomes: Mapped[list[str]] = mapped_column(json_type(), default=list)
    links: Mapped[list[dict[str, str]]] = mapped_column(json_type(), default=list)
    repository_url: Mapped[str | None] = mapped_column(String(2048))
    live_url: Mapped[str | None] = mapped_column(String(2048))
    is_open_source: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    repository_metadata_refresh_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    nature: Mapped[ProjectNature] = mapped_column(
        _string_enum(ProjectNature, length=24),
        default=ProjectNature.CASE_STUDY,
        server_default=ProjectNature.CASE_STUDY.value,
    )
    featured_rank: Mapped[int | None] = mapped_column(Integer)
    seo_title: Mapped[str | None] = mapped_column(String(200))
    seo_description: Mapped[str | None] = mapped_column(String(320))

    category: Mapped[ProfessionalCategory | None] = relationship(
        back_populates="projects", lazy="joined"
    )
    skills: Mapped[list[Skill]] = relationship(
        secondary=project_skills, back_populates="projects", lazy="selectin"
    )
    sectors: Mapped[list[Sector]] = relationship(
        secondary=project_sectors, back_populates="projects", lazy="selectin"
    )
    experiences: Mapped[list[Experience]] = relationship(
        secondary=experience_projects, back_populates="projects", lazy="selectin"
    )
    media: Mapped[list[ProjectMedia]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )
    metrics: Mapped[list[ImpactMetric]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )
    testimonials: Mapped[list[Testimonial]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )
    repository_metadata: Mapped[RepositoryMetadataSnapshot | None] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="joined",
    )


class RepositoryMetadataSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "repository_metadata_snapshots"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_repository_metadata_project"),
        CheckConstraint("stars IS NULL OR stars >= 0", name="ck_repository_metadata_stars"),
        CheckConstraint("forks IS NULL OR forks >= 0", name="ck_repository_metadata_forks"),
        Index("ix_repository_metadata_refresh", "status", "stale_after"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40), default="github", server_default="github")
    repository_identity: Mapped[str | None] = mapped_column(String(300))
    language: Mapped[str | None] = mapped_column(String(120))
    stars: Mapped[int | None] = mapped_column(Integer)
    forks: Mapped[int | None] = mapped_column(Integer)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stale_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_etag: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[RepositorySnapshotStatus] = mapped_column(
        _string_enum(RepositorySnapshotStatus, length=24),
        default=RepositorySnapshotStatus.STALE,
        server_default=RepositorySnapshotStatus.STALE.value,
    )
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refresh_token: Mapped[str | None] = mapped_column(String(36))
    refresh_lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="repository_metadata")


class ProjectMedia(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, Base):
    __tablename__ = "project_media"
    __table_args__ = (
        CheckConstraint(
            "storage_key IS NOT NULL OR external_url IS NOT NULL", name="ck_project_media_source"
        ),
        Index("ix_project_media_order", "project_id", "sort_order"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str | None] = mapped_column(String(512), unique=True)
    external_url: Mapped[str | None] = mapped_column(String(2048))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))
    alt_text: Mapped[str] = mapped_column(String(300))
    is_decorative: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    caption: Mapped[str | None] = mapped_column(String(500))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    page_count: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    project: Mapped[Project] = relationship(back_populates="media")


class PortfolioEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Structured review evidence owned by exactly one metric or testimonial."""

    __tablename__ = "portfolio_evidence"
    __table_args__ = (
        CheckConstraint(
            "(impact_metric_id IS NOT NULL AND testimonial_id IS NULL) OR "
            "(impact_metric_id IS NULL AND testimonial_id IS NOT NULL)",
            name="ck_portfolio_evidence_single_subject",
        ),
        CheckConstraint(
            "(kind = 'public_url' AND reference_url IS NOT NULL "
            "AND managed_media_id IS NULL AND reference_text IS NULL) OR "
            "(kind = 'managed_media' AND reference_url IS NULL "
            "AND managed_media_id IS NOT NULL AND reference_text IS NULL) OR "
            "(kind = 'document_reference' AND reference_url IS NULL "
            "AND managed_media_id IS NULL AND reference_text IS NOT NULL)",
            name="ck_portfolio_evidence_locator",
        ),
        CheckConstraint(
            "visibility != 'public' OR "
            "(public_label IS NOT NULL AND length(trim(public_label)) >= 3)",
            name="ck_portfolio_evidence_public_label",
        ),
        CheckConstraint("revision > 0", name="ck_portfolio_evidence_revision"),
        UniqueConstraint("impact_metric_id", name="uq_portfolio_evidence_metric"),
        UniqueConstraint("testimonial_id", name="uq_portfolio_evidence_testimonial"),
        Index("ix_portfolio_evidence_media", "managed_media_id"),
    )

    impact_metric_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("impact_metrics.id", ondelete="CASCADE")
    )
    testimonial_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("testimonials.id", ondelete="CASCADE")
    )
    kind: Mapped[EvidenceKind] = mapped_column(_string_enum(EvidenceKind, length=32))
    visibility: Mapped[EvidenceVisibility] = mapped_column(
        _string_enum(EvidenceVisibility, length=24),
        default=EvidenceVisibility.PRIVATE_REVIEW,
        server_default=EvidenceVisibility.PRIVATE_REVIEW.value,
    )
    reference_url: Mapped[str | None] = mapped_column(String(2048))
    managed_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("project_media.id", ondelete="SET NULL")
    )
    reference_text: Mapped[str | None] = mapped_column(String(2048))
    public_label: Mapped[str | None] = mapped_column(String(160))
    provenance: Mapped[str] = mapped_column(String(500))
    captured_at: Mapped[date] = mapped_column(Date)
    reviewer_note: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    metric: Mapped[ImpactMetric | None] = relationship(back_populates="evidence")
    testimonial: Mapped[Testimonial | None] = relationship(back_populates="evidence")
    managed_media: Mapped[ProjectMedia | None] = relationship(lazy="joined")


class ImpactMetric(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "impact_metrics"
    __table_args__ = (
        CheckConstraint(
            "NOT is_approved OR (approved_revision_hash IS NOT NULL "
            "AND length(approved_revision_hash) = 64 AND approved_at IS NOT NULL "
            "AND approved_by_admin_id IS NOT NULL)",
            name="ck_metric_approval_revision",
        ),
        CheckConstraint(
            "project_id IS NOT NULL OR experience_id IS NOT NULL OR "
            "(subject_label IS NOT NULL AND length(trim(subject_label)) > 0)",
            name="ck_metric_subject",
        ),
        Index("ix_metrics_public_order", "status", "is_visible", "sort_order"),
        Index("ix_metrics_project", "project_id", "sort_order"),
    )

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    experience_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("experiences.id", ondelete="CASCADE"), index=True
    )
    subject_label: Mapped[str | None] = mapped_column(String(200))
    label: Mapped[str] = mapped_column(String(160))
    value: Mapped[str] = mapped_column(String(100))
    unit: Mapped[str | None] = mapped_column(String(80))
    context: Mapped[str] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    approved_revision_hash: Mapped[str | None] = mapped_column(String(64))
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    project: Mapped[Project | None] = relationship(back_populates="metrics")
    experience: Mapped[Experience | None] = relationship(lazy="joined")
    evidence: Mapped[PortfolioEvidence | None] = relationship(
        back_populates="metric", cascade="all, delete-orphan", uselist=False, lazy="joined"
    )


class Testimonial(UUIDPrimaryKeyMixin, TimestampMixin, SeededMixin, PublishableMixin, Base):
    __tablename__ = "testimonials"
    __table_args__ = (
        CheckConstraint(
            "NOT is_approved OR (approved_revision_hash IS NOT NULL "
            "AND length(approved_revision_hash) = 64 AND approved_at IS NOT NULL "
            "AND approved_by_admin_id IS NOT NULL)",
            name="ck_testimonial_approval_revision",
        ),
        CheckConstraint(
            "project_id IS NOT NULL OR experience_id IS NOT NULL OR "
            "(subject_label IS NOT NULL AND length(trim(subject_label)) > 0)",
            name="ck_testimonial_subject",
        ),
        Index("ix_testimonials_public_order", "status", "is_visible", "sort_order"),
        Index("ix_testimonials_project", "project_id", "sort_order"),
    )

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    experience_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("experiences.id", ondelete="CASCADE"), index=True
    )
    subject_label: Mapped[str | None] = mapped_column(String(200))
    quote: Mapped[str] = mapped_column(Text)
    attribution_name: Mapped[str] = mapped_column(String(160))
    attribution_title: Mapped[str | None] = mapped_column(String(160))
    attribution_organization: Mapped[str | None] = mapped_column(String(200))
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    approved_revision_hash: Mapped[str | None] = mapped_column(String(64))
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    project: Mapped[Project | None] = relationship(back_populates="testimonials")
    experience: Mapped[Experience | None] = relationship(lazy="joined")
    evidence: Mapped[PortfolioEvidence | None] = relationship(
        back_populates="testimonial", cascade="all, delete-orphan", uselist=False, lazy="joined"
    )


class PortfolioApprovalEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only audit trail for evidence-backed approval state transitions."""

    __tablename__ = "portfolio_approval_events"
    __table_args__ = (
        CheckConstraint(
            "subject_type IN ('metric', 'testimonial')",
            name="ck_portfolio_approval_event_subject_type",
        ),
        Index("ix_portfolio_approval_events_subject", "subject_type", "subject_id", "created_at"),
    )

    subject_type: Mapped[str] = mapped_column(String(16))
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    action: Mapped[ApprovalAction] = mapped_column(_string_enum(ApprovalAction, length=24))
    actor_admin_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    revision_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
