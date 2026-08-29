from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from packages.python.clients.repository_metadata import (
    RepositoryMetadataClient,
    RepositoryMetadataProviderError,
)
from packages.python.clients.storage import StorageClient
from packages.python.common.errors import ConflictError, NotFoundError, ValidationError
from packages.python.common.models import Base, PublicationStatus
from packages.python.common.policies import PublicationPolicy
from packages.python.common.repository import TransactionManager
from packages.python.common.schemas import Page
from packages.python.common.settings import Settings
from packages.python.common.uploads import validate_declared_metadata, validate_generic_media
from services.portfolio.contracts import PortfolioPublicReader
from services.portfolio.models import (
    ApprovalAction,
    Certification,
    Education,
    EvidenceKind,
    EvidenceVisibility,
    Experience,
    ImpactMetric,
    PortfolioApprovalEvent,
    PortfolioEvidence,
    ProfessionalCategory,
    Project,
    ProjectMedia,
    ProjectNature,
    RepositoryMetadataSnapshot,
    RepositorySnapshotStatus,
    Sector,
    Skill,
    Testimonial,
)
from services.portfolio.repository import PortfolioRepository
from services.portfolio.schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    CertificationCreate,
    CertificationRead,
    CertificationUpdate,
    EducationCreate,
    EducationRead,
    EducationUpdate,
    EvidenceInput,
    ExperienceCreate,
    ExperienceRead,
    ExperienceUpdate,
    FeaturedProjectOrderRead,
    FeaturedProjectOrderUpdate,
    MetricCreate,
    MetricRead,
    MetricUpdate,
    ProjectCreate,
    ProjectMediaCreate,
    ProjectMediaRead,
    ProjectMediaUpdate,
    ProjectMediaUploadMetadata,
    ProjectRead,
    ProjectUpdate,
    PublicEvidenceRead,
    PublicMetricRead,
    PublicProjectRead,
    PublicProjectSummaryRead,
    PublicRepositoryMetadataRead,
    PublicSectorDetailRead,
    PublicSkillRead,
    PublicTestimonialRead,
    RepositoryMetadataAdminRead,
    SectorCreate,
    SectorRead,
    SectorUpdate,
    SkillCreate,
    SkillRead,
    SkillSummary,
    SkillUpdate,
    TestimonialCreate,
    TestimonialRead,
    TestimonialUpdate,
    _validate_media_accessibility,
)

ModelT = TypeVar("ModelT", bound=Base)
SchemaT = TypeVar("SchemaT", bound=BaseModel)
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(value: str, fallback: str) -> str:
    name = Path(value).name.strip().replace("\x00", "")
    return (_SAFE_FILENAME.sub("-", name).strip(".-") or fallback)[:255]


def _payload(data: BaseModel, *, exclude_unset: bool = False) -> dict[str, Any]:
    values = data.model_dump(exclude_unset=exclude_unset)
    for key, value in list(values.items()):
        if value is not None and (key.endswith("_url") or key in {"url"}):
            values[key] = str(value)
    if "links" in values and values["links"] is not None:
        values["links"] = [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item
            for item in values["links"]
        ]
    return values


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class PortfolioService(PortfolioPublicReader):
    def __init__(
        self,
        repository: PortfolioRepository,
        transaction: TransactionManager,
        storage: StorageClient,
        settings: Settings,
        repository_metadata_client: RepositoryMetadataClient | None = None,
    ) -> None:
        self.repository = repository
        self.transaction = transaction
        self.storage = storage
        self.settings = settings
        self.repository_metadata_client = repository_metadata_client

    async def create_category(self, data: CategoryCreate) -> CategoryRead:
        return await self._create_simple(ProfessionalCategory, data, CategoryRead)

    async def update_category(self, entity_id: UUID, data: CategoryUpdate) -> CategoryRead:
        return await self._update_simple(ProfessionalCategory, entity_id, data, CategoryRead)

    async def create_sector(self, data: SectorCreate) -> SectorRead:
        return await self._create_simple(Sector, data, SectorRead)

    async def update_sector(self, entity_id: UUID, data: SectorUpdate) -> SectorRead:
        return await self._update_simple(Sector, entity_id, data, SectorRead)

    async def create_skill(self, data: SkillCreate) -> SkillRead:
        category = None
        if data.category_id:
            category = await self._require_relation(
                ProfessionalCategory, data.category_id, "category_id"
            )
        payload = _payload(data)
        status = PublicationStatus(payload.pop("status"))
        skill = Skill(**payload)
        skill.category = category
        PublicationPolicy.apply(skill, status)
        self.repository.add(skill)
        await self._commit_conflict("A skill with this slug already exists.")
        return SkillRead.model_validate(skill)

    async def update_skill(self, entity_id: UUID, data: SkillUpdate) -> SkillRead:
        skill = await self._require(Skill, entity_id, "Skill")
        payload = _payload(data, exclude_unset=True)
        if "category_id" in payload:
            category_id = payload.pop("category_id")
            skill.category = (
                await self._require_relation(ProfessionalCategory, category_id, "category_id")
                if category_id
                else None
            )
        return await self._apply_update(skill, payload, SkillRead)

    async def create_experience(self, data: ExperienceCreate) -> ExperienceRead:
        payload = _payload(data)
        skill_ids = payload.pop("skill_ids")
        sector_ids = payload.pop("sector_ids")
        project_ids = payload.pop("project_ids")
        status = PublicationStatus(payload.pop("status"))
        experience = Experience(**payload)
        experience.skills = await self._resolve(Skill, skill_ids, "skill")
        experience.sectors = await self._resolve(Sector, sector_ids, "sector")
        experience.projects = await self._resolve(Project, project_ids, "project")
        PublicationPolicy.apply(experience, status)
        self.repository.add(experience)
        await self._commit_conflict("Experience relationships or values conflict.")
        loaded = await self.repository.get(Experience, experience.id)
        return ExperienceRead.model_validate(loaded or experience)

    async def update_experience(self, entity_id: UUID, data: ExperienceUpdate) -> ExperienceRead:
        experience = await self._require(Experience, entity_id, "Experience")
        payload = _payload(data, exclude_unset=True)
        if "skill_ids" in payload:
            experience.skills = await self._resolve(Skill, payload.pop("skill_ids"), "skill")
        if "sector_ids" in payload:
            experience.sectors = await self._resolve(Sector, payload.pop("sector_ids"), "sector")
        if "project_ids" in payload:
            experience.projects = await self._resolve(
                Project, payload.pop("project_ids"), "project"
            )
        self._validate_dates(experience, payload)
        for key, value in payload.items():
            setattr(experience, key, value)
        await self._commit_conflict("Experience relationships or values conflict.")
        loaded = await self.repository.get(Experience, experience.id)
        return ExperienceRead.model_validate(loaded or experience)

    async def create_education(self, data: EducationCreate) -> EducationRead:
        return await self._create_simple(Education, data, EducationRead)

    async def update_education(self, entity_id: UUID, data: EducationUpdate) -> EducationRead:
        entity = await self._require(Education, entity_id, "Education entry")
        payload = _payload(data, exclude_unset=True)
        self._validate_dates(entity, payload)
        return await self._apply_update(entity, payload, EducationRead)

    async def create_certification(self, data: CertificationCreate) -> CertificationRead:
        return await self._create_simple(Certification, data, CertificationRead)

    async def update_certification(
        self, entity_id: UUID, data: CertificationUpdate
    ) -> CertificationRead:
        certification = await self._require(Certification, entity_id, "Certification")
        payload = _payload(data, exclude_unset=True)
        issued_on = payload.get("issued_on", certification.issued_on)
        expires_on = payload.get("expires_on", certification.expires_on)
        if issued_on and expires_on and expires_on < issued_on:
            raise ValidationError("expires_on cannot precede issued_on.")
        return await self._apply_update(certification, payload, CertificationRead)

    async def create_project(self, data: ProjectCreate) -> ProjectRead:
        payload = _payload(data)
        skill_ids = payload.pop("skill_ids")
        sector_ids = payload.pop("sector_ids")
        status = PublicationStatus(payload.pop("status"))
        if payload.get("nature") is None:
            payload["nature"] = (
                ProjectNature.SOFTWARE
                if payload.get("is_open_source")
                else ProjectNature.CASE_STUDY
            )
        self._validate_repository_refresh_configuration(
            is_open_source=bool(payload.get("is_open_source")),
            repository_url=payload.get("repository_url"),
            enabled=bool(payload.get("repository_metadata_refresh_enabled")),
        )
        category_id = payload.get("category_id")
        if category_id:
            await self._require_relation(ProfessionalCategory, category_id, "category_id")
        project = Project(**payload)
        project.skills = await self._resolve(Skill, skill_ids, "skill")
        project.sectors = await self._resolve(Sector, sector_ids, "sector")
        PublicationPolicy.apply(project, status)
        self.repository.add(project)
        await self._commit_project()
        loaded = await self.repository.get(Project, project.id)
        return ProjectRead.model_validate(loaded or project)

    async def update_project(self, entity_id: UUID, data: ProjectUpdate) -> ProjectRead:
        project = await self.repository.get_project_for_update(entity_id)
        if project is None:
            raise NotFoundError("Project not found.")
        payload = _payload(data, exclude_unset=True)
        if payload.get("is_open_source") is True and "nature" not in payload:
            payload["nature"] = ProjectNature.SOFTWARE
        repository_changed = (
            "repository_url" in payload and payload["repository_url"] != project.repository_url
        )
        if payload.get("category_id"):
            await self._require_relation(
                ProfessionalCategory, payload["category_id"], "category_id"
            )
        if "skill_ids" in payload:
            project.skills = await self._resolve(Skill, payload.pop("skill_ids"), "skill")
        if "sector_ids" in payload:
            project.sectors = await self._resolve(Sector, payload.pop("sector_ids"), "sector")
        self._validate_dates(project, payload)
        for key, value in payload.items():
            setattr(project, key, value)
        if not project.is_open_source:
            project.repository_metadata_refresh_enabled = False
        self._validate_repository_refresh_configuration(
            is_open_source=project.is_open_source,
            repository_url=project.repository_url,
            enabled=project.repository_metadata_refresh_enabled,
        )
        if repository_changed and project.repository_metadata is not None:
            self._clear_repository_snapshot(project.repository_metadata)
        if not project.is_visible:
            project.featured_rank = None
        await self._commit_project()
        loaded = await self.repository.get(Project, project.id)
        return ProjectRead.model_validate(loaded or project)

    async def refresh_repository_metadata(
        self, project_id: UUID, *, force: bool = False
    ) -> RepositoryMetadataAdminRead:
        if self.repository_metadata_client is None:
            raise ConflictError("Repository metadata refresh is not configured.")
        now = datetime.now(UTC)
        project = await self.repository.get_project_for_update(project_id)
        if project is None:
            raise NotFoundError("Project not found.")
        self._validate_repository_refresh_configuration(
            is_open_source=project.is_open_source,
            repository_url=project.repository_url,
            enabled=project.repository_metadata_refresh_enabled,
        )
        if project.repository_url is None:
            raise ConflictError("The project has no repository URL.")
        # Read the one-to-one row after taking the project lock. A concurrent first
        # refresh may have inserted it while this request waited for that lock.
        snapshot = await self.repository.get_repository_snapshot_for_update(project_id)
        if snapshot is None:
            snapshot = self.repository.add_repository_snapshot(
                RepositoryMetadataSnapshot(project_id=project.id)
            )
            await self.repository.flush()
        if (
            not force
            and snapshot.fetched_at is not None
            and snapshot.stale_after is not None
            and _as_utc(snapshot.stale_after) > now
            and snapshot.status is RepositorySnapshotStatus.FRESH
        ):
            return RepositoryMetadataAdminRead.model_validate(snapshot)
        if (
            snapshot.status is RepositorySnapshotStatus.REFRESHING
            and snapshot.refresh_lease_until is not None
            and _as_utc(snapshot.refresh_lease_until) > now
        ):
            raise ConflictError("Repository metadata is already being refreshed.")
        # `force` bypasses the local freshness TTL, not a provider-imposed retry
        # window. Persisting Retry-After is only useful if every refresh path obeys
        # it; returning the reviewed stale snapshot also keeps this command idempotent.
        if snapshot.retry_after is not None and _as_utc(snapshot.retry_after) > now:
            return RepositoryMetadataAdminRead.model_validate(snapshot)

        token = str(uuid.uuid4())
        snapshot.status = RepositorySnapshotStatus.REFRESHING
        snapshot.refresh_token = token
        snapshot.refresh_lease_until = now + timedelta(seconds=60)
        await self.transaction.commit()

        try:
            result = await self.repository_metadata_client.fetch(
                project.repository_url,
                etag=snapshot.provider_etag,
            )
        except RepositoryMetadataProviderError as exc:
            current = await self.repository.get_repository_snapshot_for_update(project_id)
            if current is None or current.refresh_token != token:
                raise ConflictError("Repository metadata refresh ownership changed.") from exc
            current.status = (
                RepositorySnapshotStatus.RATE_LIMITED
                if exc.code == "rate_limited"
                else RepositorySnapshotStatus.UNAVAILABLE
            )
            current.last_error_code = exc.code
            current.last_error_at = datetime.now(UTC)
            current.retry_after = current.last_error_at + timedelta(
                seconds=exc.retry_after_seconds or 900
            )
            current.refresh_token = None
            current.refresh_lease_until = None
            await self.transaction.commit()
            return RepositoryMetadataAdminRead.model_validate(current)

        current = await self.repository.get_repository_snapshot_for_update(project_id)
        if current is None or current.refresh_token != token:
            raise ConflictError("Repository metadata refresh ownership changed.")
        if result.not_modified:
            if current.fetched_at is None or current.repository_identity is None:
                current.status = RepositorySnapshotStatus.UNAVAILABLE
                current.last_error_code = "invalid_not_modified_response"
                current.last_error_at = datetime.now(UTC)
            else:
                current.fetched_at = result.fetched_at
                current.stale_after = result.fetched_at + timedelta(
                    seconds=self.settings.repository_metadata_refresh_ttl_seconds
                )
                current.status = RepositorySnapshotStatus.FRESH
                current.last_error_code = None
                current.last_error_at = None
                current.retry_after = None
        else:
            current.provider = result.provider
            current.repository_identity = result.repository_identity
            current.language = result.language
            current.stars = result.stars
            current.forks = result.forks
            current.fetched_at = result.fetched_at
            current.stale_after = result.fetched_at + timedelta(
                seconds=self.settings.repository_metadata_refresh_ttl_seconds
            )
            current.provider_etag = result.etag
            current.status = RepositorySnapshotStatus.FRESH
            current.last_error_code = None
            current.last_error_at = None
            current.retry_after = None
        current.refresh_token = None
        current.refresh_lease_until = None
        await self.transaction.commit()
        return RepositoryMetadataAdminRead.model_validate(current)

    async def replace_featured_order(self, data: FeaturedProjectOrderUpdate) -> list[ProjectRead]:
        """Atomically replace active featured slots; row locks serialize competing editors."""

        if len(data.project_ids) > self.settings.featured_project_limit:
            raise ValidationError(
                f"At most {self.settings.featured_project_limit} projects may be featured."
            )
        projects = list(await self.repository.list_featured_projects_for_update(data.project_ids))
        by_id = {project.id: project for project in projects}
        missing = [project_id for project_id in data.project_ids if project_id not in by_id]
        if missing:
            raise NotFoundError("One or more featured projects were not found.")
        for project_id in data.project_ids:
            project = by_id[project_id]
            if not self._is_active_featured_candidate(project):
                raise ConflictError(
                    f"Project '{project.title}' must be published and visible before featuring."
                )
        for project in projects:
            project.featured_rank = None
        try:
            await self.repository.flush()
            for rank, project_id in enumerate(data.project_ids, start=1):
                by_id[project_id].featured_rank = rank
            await self.transaction.commit()
        except IntegrityError as exc:
            await self.transaction.rollback()
            raise ConflictError(
                "Featured slots changed concurrently. Reload the occupied slots and retry."
            ) from exc
        return [ProjectRead.model_validate(by_id[item]) for item in data.project_ids]

    async def get_featured_order(self) -> FeaturedProjectOrderRead:
        projects = await self.repository.list_active_featured_projects(
            limit=self.settings.featured_project_limit
        )
        return FeaturedProjectOrderRead(
            limit=self.settings.featured_project_limit,
            projects=[ProjectRead.model_validate(project) for project in projects],
        )

    async def create_project_media(self, data: ProjectMediaCreate) -> ProjectMediaRead:
        await self._require_relation(Project, data.project_id, "project_id")
        payload = _payload(data)
        media = ProjectMedia(**payload, storage_key=None, original_filename=None)
        self.repository.add(media)
        await self.transaction.commit()
        return ProjectMediaRead.model_validate(media)

    async def upload_project_media(
        self,
        metadata: ProjectMediaUploadMetadata,
        *,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> ProjectMediaRead:
        await self._require_relation(Project, metadata.project_id, "project_id")
        upload = validate_generic_media(content, content_type, self.settings.max_media_bytes)
        self._validate_media_accessibility(
            upload.media_type,
            metadata.alt_text,
            metadata.caption,
            metadata.is_decorative,
        )
        validate_declared_metadata(
            upload,
            width=metadata.width,
            height=metadata.height,
            duration_seconds=metadata.duration_seconds,
        )
        media_id = uuid.uuid4()
        storage_key = f"projects/{metadata.project_id}/{media_id}{upload.extension}"
        stored = await self.storage.save(storage_key, upload.content)
        media = ProjectMedia(
            id=media_id,
            project_id=metadata.project_id,
            storage_key=stored.key,
            external_url=None,
            original_filename=_safe_filename(filename, f"project-media{upload.extension}"),
            media_type=upload.media_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            alt_text=metadata.alt_text,
            is_decorative=metadata.is_decorative,
            caption=metadata.caption,
            width=upload.width,
            height=upload.height,
            duration_seconds=upload.duration_seconds,
            page_count=upload.page_count,
            sort_order=metadata.sort_order,
            is_visible=metadata.is_visible,
        )
        self.repository.add(media)
        try:
            await self._commit_conflict("Project media values conflict.")
        except Exception:
            await self.storage.delete(storage_key)
            raise
        return ProjectMediaRead.model_validate(media)

    async def read_public_project_media(self, media_id: UUID) -> tuple[ProjectMediaRead, bytes]:
        media_read, storage_key = await self.get_public_project_media_file(media_id)
        return media_read, await self.storage.read(storage_key)

    async def get_public_project_media_file(self, media_id: UUID) -> tuple[ProjectMediaRead, str]:
        media = await self.repository.get_public_project_media(media_id)
        if media is None or media.storage_key is None:
            raise NotFoundError("Project media not found.")
        return ProjectMediaRead.model_validate(media), media.storage_key

    async def archive_project_media(self, media_id: UUID) -> ProjectMediaRead:
        media = await self.repository.get_project_media(media_id)
        if media is None:
            raise NotFoundError("Project media not found.")
        await self._invalidate_evidence_for_media(media_id)
        media.is_visible = False
        await self.transaction.commit()
        return ProjectMediaRead.model_validate(media)

    async def update_project_media(
        self, media_id: UUID, data: ProjectMediaUpdate
    ) -> ProjectMediaRead:
        media = await self.repository.get_project_media(media_id)
        if media is None:
            raise NotFoundError("Project media not found.")
        payload = _payload(data, exclude_unset=True)
        if payload.get("project_id"):
            await self._require_relation(Project, payload["project_id"], "project_id")
        if (
            "external_url" in payload
            and payload["external_url"] is None
            and media.storage_key is None
        ):
            raise ValidationError("Project media must retain an external or stored source.")
        if any(
            key in payload and payload[key] != getattr(media, key)
            for key in {"project_id", "external_url", "media_type", "is_visible"}
        ):
            await self._invalidate_evidence_for_media(media_id)
        for key, value in payload.items():
            setattr(media, key, value)
        self._validate_media_accessibility(
            media.media_type, media.alt_text, media.caption, media.is_decorative
        )
        await self._commit_conflict("Project media values conflict.")
        return ProjectMediaRead.model_validate(media)

    async def create_metric(self, data: MetricCreate, actor_id: UUID | None = None) -> MetricRead:
        await self._validate_subject(data.project_id, data.experience_id, data.subject_label)
        evidence_input = data.evidence
        managed_media: ProjectMedia | None = None
        if evidence_input is not None:
            managed_media = await self._validate_evidence_input(evidence_input)
        payload = _payload(data)
        payload.pop("evidence")
        status = PublicationStatus(payload.pop("status"))
        metric = ImpactMetric(**payload, created_by_admin_id=actor_id)
        if evidence_input is not None:
            metric.evidence = self._new_evidence(evidence_input, managed_media=managed_media)
        else:
            metric.evidence = None
        PublicationPolicy.apply(metric, status)
        self.repository.add(metric)
        await self._commit_conflict("Metric values or evidence conflict.")
        return MetricRead.model_validate(metric)

    async def update_metric(
        self, entity_id: UUID, data: MetricUpdate, actor_id: UUID | None = None
    ) -> MetricRead:
        # Claim edits and approval commands must serialize on the same subject row.
        # Otherwise an approval can commit against the old revision while a concurrent
        # editor commits new claim text without observing (and revoking) that approval.
        metric = await self.repository.get_metric_for_update(entity_id)
        if metric is None:
            raise NotFoundError("Metric not found.")
        payload = _payload(data, exclude_unset=True)
        evidence_changed = "evidence" in data.model_fields_set
        evidence_input = data.evidence if evidence_changed else None
        managed_media: ProjectMedia | None = None
        payload.pop("evidence", None)
        project_id = payload.get("project_id", metric.project_id)
        experience_id = payload.get("experience_id", metric.experience_id)
        subject_label = payload.get("subject_label", metric.subject_label)
        await self._validate_subject(project_id, experience_id, subject_label)
        if evidence_changed and evidence_input is not None:
            managed_media = await self._validate_evidence_input(evidence_input)
        if (
            metric.is_approved
            and any(
                key in payload
                for key in {
                    "project_id",
                    "experience_id",
                    "subject_label",
                    "label",
                    "value",
                    "unit",
                    "context",
                }
            )
        ) or (metric.is_approved and evidence_changed):
            self._revoke_metric(metric, actor_id=actor_id, automatic=True)
        if evidence_changed:
            self._replace_evidence(metric, evidence_input, managed_media=managed_media)
        return await self._apply_update(metric, payload, MetricRead)

    async def approve_metric(self, metric_id: UUID, admin_id: UUID) -> MetricRead:
        metric = await self.repository.get_metric_for_update(metric_id)
        if metric is None:
            raise NotFoundError("Metric not found.")
        await self._validate_approval(metric)
        revision_hash = self._metric_revision_hash(metric)
        if metric.is_approved and metric.approved_revision_hash == revision_hash:
            return MetricRead.model_validate(metric)
        metric.is_approved = True
        metric.approved_at = datetime.now(UTC)
        metric.approved_by_admin_id = admin_id
        metric.approved_revision_hash = revision_hash
        self.repository.add_approval_event(
            PortfolioApprovalEvent(
                subject_type="metric",
                subject_id=metric.id,
                action=ApprovalAction.APPROVED,
                actor_admin_id=admin_id,
                revision_hash=revision_hash,
            )
        )
        await self.transaction.commit()
        return MetricRead.model_validate(metric)

    async def revoke_metric_approval(self, metric_id: UUID, admin_id: UUID) -> MetricRead:
        metric = await self.repository.get_metric_for_update(metric_id)
        if metric is None:
            raise NotFoundError("Metric not found.")
        if not metric.is_approved:
            return MetricRead.model_validate(metric)
        self._revoke_metric(metric, actor_id=admin_id, automatic=False)
        await self.transaction.commit()
        return MetricRead.model_validate(metric)

    async def create_testimonial(
        self, data: TestimonialCreate, actor_id: UUID | None = None
    ) -> TestimonialRead:
        await self._validate_subject(data.project_id, data.experience_id, data.subject_label)
        evidence_input = data.evidence
        managed_media: ProjectMedia | None = None
        if evidence_input is not None:
            managed_media = await self._validate_evidence_input(evidence_input)
        payload = _payload(data)
        payload.pop("evidence")
        status = PublicationStatus(payload.pop("status"))
        testimonial = Testimonial(**payload, created_by_admin_id=actor_id)
        if evidence_input is not None:
            testimonial.evidence = self._new_evidence(evidence_input, managed_media=managed_media)
        else:
            testimonial.evidence = None
        PublicationPolicy.apply(testimonial, status)
        self.repository.add(testimonial)
        await self._commit_conflict("Testimonial values or evidence conflict.")
        return TestimonialRead.model_validate(testimonial)

    async def update_testimonial(
        self, entity_id: UUID, data: TestimonialUpdate, actor_id: UUID | None = None
    ) -> TestimonialRead:
        # Use the approval command's lock target so material edits cannot race a
        # review and leave an approval hash attached to different quote content.
        testimonial = await self.repository.get_testimonial_for_update(entity_id)
        if testimonial is None:
            raise NotFoundError("Testimonial not found.")
        payload = _payload(data, exclude_unset=True)
        evidence_changed = "evidence" in data.model_fields_set
        evidence_input = data.evidence if evidence_changed else None
        managed_media: ProjectMedia | None = None
        payload.pop("evidence", None)
        project_id = payload.get("project_id", testimonial.project_id)
        experience_id = payload.get("experience_id", testimonial.experience_id)
        subject_label = payload.get("subject_label", testimonial.subject_label)
        await self._validate_subject(project_id, experience_id, subject_label)
        if evidence_changed and evidence_input is not None:
            managed_media = await self._validate_evidence_input(evidence_input)
        if (
            testimonial.is_approved
            and any(
                key in payload
                for key in {
                    "project_id",
                    "experience_id",
                    "subject_label",
                    "quote",
                    "attribution_name",
                    "attribution_title",
                    "attribution_organization",
                }
            )
        ) or (testimonial.is_approved and evidence_changed):
            self._revoke_testimonial(testimonial, actor_id=actor_id, automatic=True)
        if evidence_changed:
            self._replace_evidence(testimonial, evidence_input, managed_media=managed_media)
        return await self._apply_update(testimonial, payload, TestimonialRead)

    async def approve_testimonial(self, testimonial_id: UUID, admin_id: UUID) -> TestimonialRead:
        testimonial = await self.repository.get_testimonial_for_update(testimonial_id)
        if testimonial is None:
            raise NotFoundError("Testimonial not found.")
        await self._validate_approval(testimonial)
        revision_hash = self._testimonial_revision_hash(testimonial)
        if testimonial.is_approved and testimonial.approved_revision_hash == revision_hash:
            return TestimonialRead.model_validate(testimonial)
        testimonial.is_approved = True
        testimonial.approved_at = datetime.now(UTC)
        testimonial.approved_by_admin_id = admin_id
        testimonial.approved_revision_hash = revision_hash
        self.repository.add_approval_event(
            PortfolioApprovalEvent(
                subject_type="testimonial",
                subject_id=testimonial.id,
                action=ApprovalAction.APPROVED,
                actor_admin_id=admin_id,
                revision_hash=revision_hash,
            )
        )
        await self.transaction.commit()
        return TestimonialRead.model_validate(testimonial)

    async def revoke_testimonial_approval(
        self, testimonial_id: UUID, admin_id: UUID
    ) -> TestimonialRead:
        testimonial = await self.repository.get_testimonial_for_update(testimonial_id)
        if testimonial is None:
            raise NotFoundError("Testimonial not found.")
        if not testimonial.is_approved:
            return TestimonialRead.model_validate(testimonial)
        self._revoke_testimonial(testimonial, actor_id=admin_id, automatic=False)
        await self.transaction.commit()
        return TestimonialRead.model_validate(testimonial)

    async def set_status(
        self, resource: str, entity_id: UUID, status: PublicationStatus
    ) -> BaseModel:
        mapping: dict[str, tuple[type[Base], type[BaseModel]]] = {
            "categories": (ProfessionalCategory, CategoryRead),
            "sectors": (Sector, SectorRead),
            "skills": (Skill, SkillRead),
            "experiences": (Experience, ExperienceRead),
            "education": (Education, EducationRead),
            "certifications": (Certification, CertificationRead),
            "projects": (Project, ProjectRead),
            "metrics": (ImpactMetric, MetricRead),
            "testimonials": (Testimonial, TestimonialRead),
        }
        selected = mapping.get(resource)
        if selected is None:
            raise NotFoundError("Unknown portfolio resource.")
        model, schema = selected
        entity: Base
        if model is Project:
            project_entity = await self.repository.get_project_for_update(entity_id)
            if project_entity is None:
                raise NotFoundError("Project not found.")
            entity = project_entity
        else:
            entity = await self._require(model, entity_id, resource.rstrip("s").title())
        PublicationPolicy.apply(entity, status)  # type: ignore[arg-type]
        if isinstance(entity, Project) and status is not PublicationStatus.PUBLISHED:
            entity.featured_rank = None
        if isinstance(entity, Project):
            await self._commit_project()
        else:
            await self.transaction.commit()
        if model in {Project, Experience}:
            reloaded = await self.repository.get(model, entity_id)
            if reloaded is not None:
                entity = reloaded
        return schema.model_validate(entity)

    async def get_project(self, entity_id: UUID) -> ProjectRead:
        return ProjectRead.model_validate(await self._require(Project, entity_id, "Project"))

    async def get_public_project(self, slug: str) -> PublicProjectRead:
        project = await self.repository.get_public_project_by_slug(slug)
        if project is None:
            raise NotFoundError("Project not found.")
        related = await self.repository.list_related_public_projects(project, limit=3)
        return self._public_project(project).model_copy(
            update={"related_projects": [self._public_project_summary(item) for item in related]}
        )

    async def list_admin(
        self,
        resource: str,
        limit: int,
        offset: int,
        *,
        search: str | None = None,
        status: PublicationStatus | None = None,
        open_source: bool | None = None,
        approved: bool | None = None,
    ) -> Page[Any]:
        mapping: dict[str, tuple[type[Base], type[BaseModel]]] = {
            "categories": (ProfessionalCategory, CategoryRead),
            "sectors": (Sector, SectorRead),
            "skills": (Skill, SkillRead),
            "experiences": (Experience, ExperienceRead),
            "education": (Education, EducationRead),
            "certifications": (Certification, CertificationRead),
            "projects": (Project, ProjectRead),
            "metrics": (ImpactMetric, MetricRead),
            "testimonials": (Testimonial, TestimonialRead),
        }
        selected = mapping.get(resource)
        if selected is None:
            raise NotFoundError("Unknown portfolio resource.")
        model, schema = selected
        entities, total = await self.repository.list_entities(
            model,
            limit=limit,
            offset=offset,
            search=search,
            status=status,
            open_source=open_source,
            approved=approved,
        )
        return Page(
            items=[schema.model_validate(entity) for entity in entities],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def list_project_media(
        self, limit: int, offset: int, *, search: str | None = None
    ) -> Page[ProjectMediaRead]:
        entities, total = await self.repository.list_active_project_media(
            limit=limit, offset=offset, search=search
        )
        return Page(
            items=[ProjectMediaRead.model_validate(entity) for entity in entities],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def list_public_categories(self, limit: int = 100) -> list[CategoryRead]:
        return await self._public_list(ProfessionalCategory, CategoryRead, limit)

    async def list_public_sectors(self, limit: int = 100) -> list[SectorRead]:
        rows = await self.repository.list_public_sectors_with_project_counts(limit=limit)
        return [
            SectorRead.model_validate(sector).model_copy(update={"project_count": project_count})
            for sector, project_count in rows
        ]

    async def list_public_skills(self, limit: int = 100) -> list[PublicSkillRead]:
        rows = await self.repository.list_public_skills_with_project_counts(limit=limit)
        return [self._public_skill(skill, project_count) for skill, project_count in rows]

    async def list_public_experiences(self, limit: int = 20) -> list[ExperienceRead]:
        entities, _ = await self.repository.list_entities(Experience, limit=limit, public=True)
        return [self._public_experience(entity) for entity in entities]

    async def list_public_education(self, limit: int = 20) -> list[EducationRead]:
        return await self._public_list(Education, EducationRead, limit)

    async def list_public_certifications(self, limit: int = 20) -> list[CertificationRead]:
        return await self._public_list(Certification, CertificationRead, limit)

    async def list_public_projects(
        self, limit: int = 20, *, featured_only: bool = False
    ) -> list[PublicProjectSummaryRead]:
        entities, _ = await self.repository.list_entities(
            Project, limit=limit, public=True, featured_only=featured_only
        )
        return [self._public_project_summary(project) for project in entities]

    async def search_public_projects(self, query: str, *, limit: int) -> list[PublicProjectRead]:
        entities = await self.repository.search_public_project_details(query, limit=limit)
        return [self._public_project(project) for project in entities]

    async def list_public_projects_page(
        self,
        *,
        limit: int,
        offset: int,
        category: str | None = None,
        sector: str | None = None,
        search: str | None = None,
        open_source: bool | None = None,
    ) -> Page[PublicProjectSummaryRead]:
        entities, total = await self.repository.list_public_projects_page(
            limit=limit,
            offset=offset,
            category=category,
            sector=sector,
            search=search,
            open_source=open_source,
        )
        return Page(
            items=[self._public_project_summary(project) for project in entities],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_public_sector(self, slug: str, *, limit: int = 100) -> PublicSectorDetailRead:
        sector = await self.repository.get_public_sector_by_slug(slug)
        if sector is None:
            raise NotFoundError("Sector not found.")
        projects, total = await self.repository.list_public_projects_page(
            limit=limit,
            offset=0,
            sector=slug,
        )
        return PublicSectorDetailRead(
            sector=SectorRead.model_validate(sector).model_copy(update={"project_count": total}),
            projects=[self._public_project_summary(project) for project in projects],
            total=total,
        )

    async def list_public_metrics(self, limit: int = 100) -> list[PublicMetricRead]:
        entities = await self.repository.list_public_approved_evidence_subjects(
            ImpactMetric, limit=limit
        )
        return [
            self._public_metric(entity) for entity in entities if isinstance(entity, ImpactMetric)
        ]

    async def list_public_testimonials(self, limit: int = 100) -> list[PublicTestimonialRead]:
        entities = await self.repository.list_public_approved_evidence_subjects(
            Testimonial, limit=limit
        )
        return [
            self._public_testimonial(entity)
            for entity in entities
            if isinstance(entity, Testimonial)
        ]

    async def _public_list(
        self, model: type[ModelT], schema: type[SchemaT], limit: int
    ) -> list[SchemaT]:
        entities, _ = await self.repository.list_entities(model, limit=limit, public=True)
        return [schema.model_validate(entity) for entity in entities]

    @staticmethod
    def _public_project(project: Project) -> PublicProjectRead:
        payload = PortfolioService._public_project_summary(project).model_dump()
        for field in (
            "description",
            "problem",
            "solution",
            "architecture",
            "features",
            "decisions",
            "tradeoffs",
            "challenges",
            "outcomes",
        ):
            payload[field] = getattr(project, field)
        payload["testimonials"] = [
            PortfolioService._public_testimonial(model)
            for model in project.testimonials
            if PortfolioService._is_public_evidence_subject(model)
        ]
        return PublicProjectRead.model_validate(payload)

    @staticmethod
    def _public_project_summary(project: Project) -> PublicProjectSummaryRead:
        computed = {"repository_metadata", "category", "skills", "sectors", "media", "metrics"}
        payload = {
            field: getattr(project, field)
            for field in PublicProjectSummaryRead.model_fields
            if field not in computed
        }
        payload["repository_metadata"] = PortfolioService._public_repository_metadata(project)
        payload["category"] = (
            CategoryRead.model_validate(project.category)
            if project.category and PortfolioService._is_public_parent(project.category)
            else None
        )
        payload["skills"] = [
            SkillSummary.model_validate(model)
            for model in project.skills
            if PortfolioService._is_public_parent(model)
        ]
        payload["sectors"] = [
            SectorRead.model_validate(model)
            for model in project.sectors
            if PortfolioService._is_public_parent(model)
        ]
        payload["media"] = [
            ProjectMediaRead.model_validate(media) for media in project.media if media.is_visible
        ]
        payload["metrics"] = [
            PortfolioService._public_metric(model)
            for model in project.metrics
            if PortfolioService._is_public_evidence_subject(model)
        ]
        return PublicProjectSummaryRead.model_validate(payload)

    @staticmethod
    def _public_repository_metadata(
        project: Project,
    ) -> PublicRepositoryMetadataRead | None:
        snapshot = project.repository_metadata
        if (
            not project.repository_metadata_refresh_enabled
            or snapshot is None
            or snapshot.fetched_at is None
            or snapshot.repository_identity is None
        ):
            return None
        now = datetime.now(UTC)
        freshness = (
            "fresh"
            if snapshot.status is RepositorySnapshotStatus.FRESH
            and snapshot.stale_after is not None
            and _as_utc(snapshot.stale_after) > now
            else "stale"
        )
        return PublicRepositoryMetadataRead(
            provider=snapshot.provider,
            repository_identity=snapshot.repository_identity,
            language=snapshot.language,
            stars=snapshot.stars,
            forks=snapshot.forks,
            fetched_at=_as_utc(snapshot.fetched_at),
            freshness=freshness,
        )

    @staticmethod
    def _public_skill(skill: Skill, project_count: int) -> PublicSkillRead:
        response = PublicSkillRead.model_validate(skill).model_copy(
            update={"project_count": project_count}
        )
        if skill.category and not PortfolioService._is_public_parent(skill.category):
            response.category = None
        return response

    @staticmethod
    def _public_metric(metric: ImpactMetric) -> PublicMetricRead:
        return PublicMetricRead.model_validate(metric).model_copy(
            update={"public_evidence": PortfolioService._public_evidence(metric.evidence)}
        )

    @staticmethod
    def _public_testimonial(testimonial: Testimonial) -> PublicTestimonialRead:
        return PublicTestimonialRead.model_validate(testimonial).model_copy(
            update={"public_evidence": PortfolioService._public_evidence(testimonial.evidence)}
        )

    @staticmethod
    def _public_evidence(evidence: PortfolioEvidence | None) -> PublicEvidenceRead | None:
        if (
            evidence is None
            or evidence.archived_at is not None
            or evidence.visibility is not EvidenceVisibility.PUBLIC
            or not evidence.public_label
        ):
            return None
        url: str | None = None
        if evidence.kind is EvidenceKind.PUBLIC_URL:
            url = evidence.reference_url
        elif evidence.kind is EvidenceKind.MANAGED_MEDIA and evidence.managed_media_id:
            if evidence.managed_media is None or not evidence.managed_media.is_visible:
                return None
            url = f"/api/v1/public/project-media/{evidence.managed_media_id}"
        return PublicEvidenceRead(
            label=evidence.public_label,
            url=url,
            captured_at=evidence.captured_at,
        )

    @staticmethod
    def _is_public_parent(entity: Any) -> bool:
        return PublicationPolicy.is_public(entity) and not entity.noindex

    @staticmethod
    def _is_public_evidence_subject(subject: ImpactMetric | Testimonial) -> bool:
        evidence = subject.evidence
        return (
            subject.is_approved
            and evidence is not None
            and evidence.archived_at is None
            and (
                evidence.kind is not EvidenceKind.MANAGED_MEDIA
                or (evidence.managed_media is not None and evidence.managed_media.is_visible)
            )
            and PortfolioService._is_public_parent(subject)
            and (subject.project is None or PortfolioService._is_public_parent(subject.project))
            and (
                subject.experience is None or PortfolioService._is_public_parent(subject.experience)
            )
        )

    @staticmethod
    def _public_experience(experience: Experience) -> ExperienceRead:
        response = ExperienceRead.model_validate(experience)
        response.skills = [
            value
            for value, model in zip(response.skills, experience.skills, strict=True)
            if PublicationPolicy.is_public(model)
        ]
        response.sectors = [
            value
            for value, model in zip(response.sectors, experience.sectors, strict=True)
            if PublicationPolicy.is_public(model)
        ]
        response.projects = [
            value
            for value, model in zip(response.projects, experience.projects, strict=True)
            if PublicationPolicy.is_public(model)
        ]
        return response

    async def _create_simple(
        self, model: type[ModelT], data: BaseModel, schema: type[SchemaT]
    ) -> SchemaT:
        payload = _payload(data)
        status = PublicationStatus(payload.pop("status"))
        entity = model(**payload)
        PublicationPolicy.apply(entity, status)  # type: ignore[arg-type]
        self.repository.add(entity)
        await self._commit_conflict("A unique value already exists or the data conflicts.")
        return schema.model_validate(entity)

    async def _update_simple(
        self,
        model: type[ModelT],
        entity_id: UUID,
        data: BaseModel,
        schema: type[SchemaT],
    ) -> SchemaT:
        entity = await self._require(model, entity_id, model.__name__)
        return await self._apply_update(entity, _payload(data, exclude_unset=True), schema)

    async def _apply_update(
        self, entity: ModelT, payload: dict[str, Any], schema: type[SchemaT]
    ) -> SchemaT:
        for key, value in payload.items():
            setattr(entity, key, value)
        await self._commit_conflict("A unique value already exists or the data conflicts.")
        return schema.model_validate(entity)

    async def _require(self, model: type[ModelT], entity_id: UUID, label: str) -> ModelT:
        entity = await self.repository.get(model, entity_id)
        if entity is None:
            raise NotFoundError(f"{label} not found.")
        return entity

    async def _require_relation(self, model: type[ModelT], entity_id: UUID, field: str) -> ModelT:
        entity = await self.repository.get(model, entity_id)
        if entity is None:
            raise ValidationError(f"{field} references a record that does not exist.")
        if getattr(entity, "archived_at", None) is not None:
            raise ValidationError(f"{field} references an archived record.")
        return entity

    async def _resolve(self, model: type[ModelT], ids: list[UUID], label: str) -> list[ModelT]:
        unique_ids = list(dict.fromkeys(ids))
        entities = await self.repository.get_many(model, unique_ids)
        if len(entities) != len(unique_ids):
            raise ValidationError(f"One or more referenced {label} IDs do not exist.")
        if any(getattr(entity, "archived_at", None) is not None for entity in entities):
            raise ValidationError(
                f"{label}_ids contains an archived record; remove or replace that relationship."
            )
        by_id = {entity.id: entity for entity in entities}  # type: ignore[attr-defined]
        return [by_id[entity_id] for entity_id in unique_ids]

    async def _validate_evidence_input(self, evidence: EvidenceInput) -> ProjectMedia | None:
        if evidence.kind is not EvidenceKind.MANAGED_MEDIA:
            return None
        if evidence.managed_media_id is None:
            raise ValidationError("Managed evidence requires a media asset.")
        media = await self.repository.get_project_media(evidence.managed_media_id)
        if media is None:
            raise ValidationError("The managed evidence asset does not exist.")
        if media.storage_key is None:
            raise ValidationError("Managed evidence must use an uploaded immutable asset.")
        if not await self.storage.exists(media.storage_key):
            raise ValidationError("The managed evidence file is missing from storage.")
        return media

    @staticmethod
    def _validate_media_accessibility(
        media_type: str, alt_text: str, caption: str | None, is_decorative: bool
    ) -> None:
        try:
            _validate_media_accessibility(media_type, alt_text, caption, is_decorative)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    @staticmethod
    def _validate_repository_refresh_configuration(
        *, is_open_source: bool, repository_url: object, enabled: bool
    ) -> None:
        if not enabled:
            return
        if not is_open_source:
            raise ValidationError("Repository metadata refresh requires an open-source project.")
        if not repository_url:
            raise ValidationError("Repository metadata refresh requires a repository URL.")

    @staticmethod
    def _clear_repository_snapshot(snapshot: RepositoryMetadataSnapshot) -> None:
        snapshot.repository_identity = None
        snapshot.language = None
        snapshot.stars = None
        snapshot.forks = None
        snapshot.fetched_at = None
        snapshot.stale_after = None
        snapshot.provider_etag = None
        snapshot.status = RepositorySnapshotStatus.STALE
        snapshot.last_error_code = None
        snapshot.last_error_at = None
        snapshot.retry_after = None
        snapshot.refresh_token = None
        snapshot.refresh_lease_until = None

    @staticmethod
    def _new_evidence(
        data: EvidenceInput, *, managed_media: ProjectMedia | None = None
    ) -> PortfolioEvidence:
        return PortfolioEvidence(
            kind=data.kind,
            visibility=data.visibility,
            reference_url=str(data.reference_url) if data.reference_url is not None else None,
            managed_media_id=data.managed_media_id,
            reference_text=data.reference_text,
            public_label=data.public_label,
            provenance=data.provenance,
            captured_at=data.captured_at,
            reviewer_note=data.reviewer_note,
            revision=1,
            managed_media=managed_media,
        )

    @staticmethod
    def _replace_evidence(
        subject: ImpactMetric | Testimonial,
        data: EvidenceInput | None,
        *,
        managed_media: ProjectMedia | None = None,
    ) -> None:
        if data is None:
            subject.evidence = None
            return
        if subject.evidence is None:
            subject.evidence = PortfolioService._new_evidence(data, managed_media=managed_media)
            return
        evidence = subject.evidence
        evidence.kind = data.kind
        evidence.visibility = data.visibility
        evidence.reference_url = str(data.reference_url) if data.reference_url else None
        evidence.managed_media_id = data.managed_media_id
        evidence.managed_media = managed_media
        evidence.reference_text = data.reference_text
        evidence.public_label = data.public_label
        evidence.provenance = data.provenance
        evidence.captured_at = data.captured_at
        evidence.reviewer_note = data.reviewer_note
        evidence.archived_at = None
        evidence.revision += 1

    async def _validate_approval(self, subject: ImpactMetric | Testimonial) -> None:
        if not self._is_public_parent(subject):
            raise ValidationError("Publish the evidence-backed record before approval.")
        if subject.project is not None and not self._is_public_parent(subject.project):
            raise ValidationError(
                "The linked project must be public and indexable before approval."
            )
        if subject.experience is not None and not self._is_public_parent(subject.experience):
            raise ValidationError(
                "The linked experience must be public and indexable before approval."
            )
        evidence = subject.evidence
        if evidence is None or evidence.archived_at is not None:
            raise ValidationError("Structured evidence is required before approval.")
        if evidence.kind is EvidenceKind.PUBLIC_URL:
            if not evidence.reference_url or not evidence.reference_url.startswith("https://"):
                raise ValidationError("Approval requires a valid HTTPS evidence URL.")
        elif evidence.kind is EvidenceKind.DOCUMENT_REFERENCE:
            if not evidence.reference_text or len(evidence.reference_text.strip()) < 12:
                raise ValidationError("Approval requires a meaningful document reference.")
        else:
            if evidence.managed_media_id is None:
                raise ValidationError("Approval requires an existing managed evidence asset.")
            media = await self.repository.get_project_media(evidence.managed_media_id)
            if media is None:
                raise ValidationError("The managed evidence asset no longer exists.")
            if media.storage_key is None:
                raise ValidationError("Managed evidence must use an uploaded immutable asset.")
            if not await self.storage.exists(media.storage_key):
                raise ValidationError("The managed evidence file is missing from storage.")
            if evidence.visibility is EvidenceVisibility.PUBLIC:
                parent = await self.repository.get(Project, media.project_id)
                if not media.is_visible or parent is None or not self._is_public_parent(parent):
                    raise ValidationError(
                        "Public managed evidence must belong to a public project."
                    )
        if evidence.visibility is EvidenceVisibility.PUBLIC and not evidence.public_label:
            raise ValidationError("Public evidence requires a reviewed public label.")

    @staticmethod
    def _evidence_revision_payload(evidence: PortfolioEvidence | None) -> dict[str, Any] | None:
        if evidence is None:
            return None
        return {
            "kind": evidence.kind.value,
            "visibility": evidence.visibility.value,
            "reference_url": evidence.reference_url,
            "managed_media_id": str(evidence.managed_media_id)
            if evidence.managed_media_id
            else None,
            "reference_text": evidence.reference_text,
            "public_label": evidence.public_label,
            "provenance": evidence.provenance,
            "captured_at": evidence.captured_at.isoformat(),
            "revision": evidence.revision,
        }

    @staticmethod
    def _revision_hash(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @classmethod
    def _metric_revision_hash(cls, metric: ImpactMetric) -> str:
        return cls._revision_hash(
            {
                "project_id": str(metric.project_id) if metric.project_id else None,
                "experience_id": str(metric.experience_id) if metric.experience_id else None,
                "subject_label": metric.subject_label,
                "label": metric.label,
                "value": metric.value,
                "unit": metric.unit,
                "context": metric.context,
                "evidence": cls._evidence_revision_payload(metric.evidence),
            }
        )

    @classmethod
    def _testimonial_revision_hash(cls, testimonial: Testimonial) -> str:
        return cls._revision_hash(
            {
                "project_id": str(testimonial.project_id) if testimonial.project_id else None,
                "experience_id": str(testimonial.experience_id)
                if testimonial.experience_id
                else None,
                "subject_label": testimonial.subject_label,
                "quote": testimonial.quote,
                "attribution_name": testimonial.attribution_name,
                "attribution_title": testimonial.attribution_title,
                "attribution_organization": testimonial.attribution_organization,
                "evidence": cls._evidence_revision_payload(testimonial.evidence),
            }
        )

    def _revoke_metric(
        self, metric: ImpactMetric, *, actor_id: UUID | None, automatic: bool
    ) -> None:
        previous_hash = metric.approved_revision_hash
        metric.is_approved = False
        metric.approved_at = None
        metric.approved_by_admin_id = None
        metric.approved_revision_hash = None
        self.repository.add_approval_event(
            PortfolioApprovalEvent(
                subject_type="metric",
                subject_id=metric.id,
                action=ApprovalAction.AUTO_REVOKED if automatic else ApprovalAction.REVOKED,
                actor_admin_id=actor_id,
                revision_hash=previous_hash,
            )
        )

    def _revoke_testimonial(
        self, testimonial: Testimonial, *, actor_id: UUID | None, automatic: bool
    ) -> None:
        previous_hash = testimonial.approved_revision_hash
        testimonial.is_approved = False
        testimonial.approved_at = None
        testimonial.approved_by_admin_id = None
        testimonial.approved_revision_hash = None
        self.repository.add_approval_event(
            PortfolioApprovalEvent(
                subject_type="testimonial",
                subject_id=testimonial.id,
                action=ApprovalAction.AUTO_REVOKED if automatic else ApprovalAction.REVOKED,
                actor_admin_id=actor_id,
                revision_hash=previous_hash,
            )
        )

    async def _invalidate_evidence_for_media(self, media_id: UUID) -> None:
        """Atomically invalidate reviews tied to a changed or archived managed source."""

        for evidence in await self.repository.list_evidence_for_media_for_update(media_id):
            if evidence.archived_at is None:
                evidence.archived_at = datetime.now(UTC)
                evidence.revision += 1
            if evidence.metric is not None and evidence.metric.is_approved:
                self._revoke_metric(evidence.metric, actor_id=None, automatic=True)
            if evidence.testimonial is not None and evidence.testimonial.is_approved:
                self._revoke_testimonial(evidence.testimonial, actor_id=None, automatic=True)

    async def _validate_subject(
        self,
        project_id: UUID | None,
        experience_id: UUID | None,
        subject_label: str | None,
    ) -> None:
        if not (project_id or experience_id or (subject_label and subject_label.strip())):
            raise ValidationError("A project, experience, or subject label is required.")
        if project_id:
            await self._require_relation(Project, project_id, "project_id")
        if experience_id:
            await self._require_relation(Experience, experience_id, "experience_id")

    @staticmethod
    def _validate_dates(entity: Any, payload: dict[str, Any]) -> None:
        start = payload.get("start_date", getattr(entity, "start_date", None))
        end = payload.get("end_date", getattr(entity, "end_date", None))
        if start and end and end < start:
            raise ValidationError("end_date cannot precede start_date.")

    async def _commit_conflict(self, message: str) -> None:
        try:
            await self.transaction.commit()
        except IntegrityError as exc:
            await self.transaction.rollback()
            raise ConflictError(message) from exc

    async def _commit_project(self) -> None:
        try:
            await self.transaction.commit()
        except IntegrityError as exc:
            await self.transaction.rollback()
            detail = str(getattr(exc, "orig", exc)).casefold()
            if "featured" in detail or "active_featured_rank" in detail:
                raise ConflictError(
                    "That featured slot is occupied by another published project. "
                    "Reload the featured order and choose an available slot."
                ) from exc
            raise ConflictError("A project with this slug already exists.") from exc

    @staticmethod
    def _is_active_featured_candidate(project: Project) -> bool:
        return (
            project.status is PublicationStatus.PUBLISHED
            and project.is_visible
            and project.archived_at is None
        )
