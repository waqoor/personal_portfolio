from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypeVar, cast

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from packages.python.common.errors import ValidationError
from packages.python.common.models import Base, PublicationStatus
from packages.python.common.policies import PublicationPolicy
from packages.python.common.repository import TransactionManager
from packages.python.common.schemas import APIModel
from packages.python.contracts.seeding import SeedKey, SeedRecord, SeedSource, SeedStats
from services.portfolio.models import (
    Certification,
    Education,
    Experience,
    ImpactMetric,
    PortfolioEvidence,
    ProfessionalCategory,
    Project,
    Sector,
    Skill,
    Testimonial,
)
from services.portfolio.repository import PortfolioRepository
from services.portfolio.schemas import (
    CategoryCreate,
    CertificationCreate,
    EducationCreate,
    EvidenceInput,
    ExperienceCreate,
    MetricCreate,
    ProjectCreate,
    SectorCreate,
    SkillCreate,
    TestimonialCreate,
)

ModelT = TypeVar("ModelT", bound=Base)


class SeedSkill(APIModel):
    seed_key: SeedKey
    category_seed_key: SeedKey | None = None
    payload: SkillCreate

    @model_validator(mode="after")
    def forbid_uuid_reference(self) -> SeedSkill:
        if self.payload.category_id is not None:
            raise ValueError("seed skills must reference categories by category_seed_key")
        return self


class SeedProject(APIModel):
    seed_key: SeedKey
    category_seed_key: SeedKey | None = None
    skill_seed_keys: list[SeedKey] = Field(default_factory=list, max_length=200)
    sector_seed_keys: list[SeedKey] = Field(default_factory=list, max_length=100)
    payload: ProjectCreate

    @model_validator(mode="after")
    def forbid_uuid_references(self) -> SeedProject:
        if self.payload.category_id or self.payload.skill_ids or self.payload.sector_ids:
            raise ValueError("seed projects must use seed-key relationship fields")
        return self


class SeedExperience(APIModel):
    seed_key: SeedKey
    skill_seed_keys: list[SeedKey] = Field(default_factory=list, max_length=200)
    sector_seed_keys: list[SeedKey] = Field(default_factory=list, max_length=100)
    project_seed_keys: list[SeedKey] = Field(default_factory=list, max_length=200)
    payload: ExperienceCreate

    @model_validator(mode="after")
    def forbid_uuid_references(self) -> SeedExperience:
        if self.payload.skill_ids or self.payload.sector_ids or self.payload.project_ids:
            raise ValueError("seed experiences must use seed-key relationship fields")
        return self


class SeedMetric(APIModel):
    seed_key: SeedKey
    project_seed_key: SeedKey | None = None
    experience_seed_key: SeedKey | None = None
    payload: MetricCreate

    @model_validator(mode="after")
    def forbid_uuid_references(self) -> SeedMetric:
        if self.payload.project_id or self.payload.experience_id:
            raise ValueError("seed metrics must use seed-key relationship fields")
        if not (self.project_seed_key or self.experience_seed_key or self.payload.subject_label):
            raise ValueError("a seeded relationship or subject_label is required")
        return self


class SeedTestimonial(APIModel):
    seed_key: SeedKey
    project_seed_key: SeedKey | None = None
    experience_seed_key: SeedKey | None = None
    payload: TestimonialCreate

    @model_validator(mode="after")
    def forbid_uuid_references(self) -> SeedTestimonial:
        if self.payload.project_id or self.payload.experience_id:
            raise ValueError("seed testimonials must use seed-key relationship fields")
        if not (self.project_seed_key or self.experience_seed_key or self.payload.subject_label):
            raise ValueError("a seeded relationship or subject_label is required")
        return self


class PortfolioSeedData(APIModel):
    categories: list[SeedRecord[CategoryCreate]] = Field(default_factory=list)
    sectors: list[SeedRecord[SectorCreate]] = Field(default_factory=list)
    skills: list[SeedSkill] = Field(default_factory=list)
    projects: list[SeedProject] = Field(default_factory=list)
    experiences: list[SeedExperience] = Field(default_factory=list)
    education: list[SeedRecord[EducationCreate]] = Field(default_factory=list)
    certifications: list[SeedRecord[CertificationCreate]] = Field(default_factory=list)
    metrics: list[SeedMetric] = Field(default_factory=list)
    testimonials: list[SeedTestimonial] = Field(default_factory=list)


def _payload(data: BaseModel) -> dict[str, Any]:
    values = data.model_dump()
    for key, value in list(values.items()):
        if value is not None and key.endswith("_url"):
            values[key] = str(value)
    if "links" in values:
        values["links"] = data.model_dump(mode="json").get("links", [])
    return values


def _evidence(data: EvidenceInput) -> PortfolioEvidence:
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
    )


class PortfolioSeeder:
    def __init__(self, repository: PortfolioRepository, transaction: TransactionManager) -> None:
        self.repository = repository
        self.transaction = transaction

    async def apply(self, data: PortfolioSeedData, *, source: SeedSource) -> SeedStats:
        stats = SeedStats()
        categories = await self._simple_group(
            data.categories, ProfessionalCategory, "slug", source, stats
        )
        sectors = await self._simple_group(data.sectors, Sector, "slug", source, stats)

        skills: dict[str, Skill] = {}
        for skill_record in data.skills:
            existing_skill = await self._existing(
                Skill, skill_record.seed_key, "slug", skill_record.payload.slug
            )
            if existing_skill:
                skills[skill_record.seed_key] = existing_skill
                stats.add_skipped()
                continue
            payload = _payload(skill_record.payload)
            status = PublicationStatus(payload.pop("status"))
            payload.pop("category_id", None)
            skill_category = await self._reference(
                ProfessionalCategory,
                skill_record.category_seed_key,
                categories,
                "category",
            )
            skill = Skill(
                **payload,
                category_id=skill_category.id if skill_category else None,
                **self._provenance(skill_record.seed_key, source),
            )
            PublicationPolicy.apply(skill, status)
            self.repository.add(skill)
            skills[skill_record.seed_key] = skill
            stats.add_created()
        await self.repository.session.flush()

        projects: dict[str, Project] = {}
        for project_record in data.projects:
            existing_project = await self._existing(
                Project, project_record.seed_key, "slug", project_record.payload.slug
            )
            if existing_project:
                projects[project_record.seed_key] = existing_project
                stats.add_skipped()
                continue
            payload = _payload(project_record.payload)
            status = PublicationStatus(payload.pop("status"))
            for key in ("category_id", "skill_ids", "sector_ids"):
                payload.pop(key, None)
            project_category = await self._reference(
                ProfessionalCategory,
                project_record.category_seed_key,
                categories,
                "category",
            )
            project = Project(
                **payload,
                category_id=project_category.id if project_category else None,
                **self._provenance(project_record.seed_key, source),
            )
            project.skills = [
                await self._required_reference(Skill, key, skills, "skill")
                for key in dict.fromkeys(project_record.skill_seed_keys)
            ]
            project.sectors = [
                await self._required_reference(Sector, key, sectors, "sector")
                for key in dict.fromkeys(project_record.sector_seed_keys)
            ]
            PublicationPolicy.apply(project, status)
            self.repository.add(project)
            projects[project_record.seed_key] = project
            stats.add_created()
        await self.repository.session.flush()

        experiences: dict[str, Experience] = {}
        for experience_record in data.experiences:
            existing_experience = await self.repository.get_by_seed_key(
                Experience, experience_record.seed_key
            )
            if existing_experience:
                experiences[experience_record.seed_key] = existing_experience
                stats.add_skipped()
                continue
            payload = _payload(experience_record.payload)
            status = PublicationStatus(payload.pop("status"))
            for key in ("skill_ids", "sector_ids", "project_ids"):
                payload.pop(key, None)
            experience = Experience(
                **payload, **self._provenance(experience_record.seed_key, source)
            )
            experience.skills = [
                await self._required_reference(Skill, key, skills, "skill")
                for key in dict.fromkeys(experience_record.skill_seed_keys)
            ]
            experience.sectors = [
                await self._required_reference(Sector, key, sectors, "sector")
                for key in dict.fromkeys(experience_record.sector_seed_keys)
            ]
            experience.projects = [
                await self._required_reference(Project, key, projects, "project")
                for key in dict.fromkeys(experience_record.project_seed_keys)
            ]
            PublicationPolicy.apply(experience, status)
            self.repository.add(experience)
            experiences[experience_record.seed_key] = experience
            stats.add_created()
        await self.repository.session.flush()

        await self._simple_group(data.education, Education, None, source, stats)
        await self._simple_group(data.certifications, Certification, None, source, stats)

        for metric_record in data.metrics:
            if await self.repository.get_by_seed_key(ImpactMetric, metric_record.seed_key):
                stats.add_skipped()
                continue
            payload = _payload(metric_record.payload)
            payload.pop("evidence")
            status = PublicationStatus(payload.pop("status"))
            payload.pop("project_id", None)
            payload.pop("experience_id", None)
            metric_project = await self._reference(
                Project, metric_record.project_seed_key, projects, "project"
            )
            metric_experience = await self._reference(
                Experience,
                metric_record.experience_seed_key,
                experiences,
                "experience",
            )
            metric = ImpactMetric(
                **payload,
                project_id=metric_project.id if metric_project else None,
                experience_id=metric_experience.id if metric_experience else None,
                is_approved=False,
                **self._provenance(metric_record.seed_key, source),
            )
            if metric_record.payload.evidence is not None:
                metric.evidence = _evidence(metric_record.payload.evidence)
            PublicationPolicy.apply(metric, status)
            self.repository.add(metric)
            stats.add_created()

        for testimonial_record in data.testimonials:
            if await self.repository.get_by_seed_key(Testimonial, testimonial_record.seed_key):
                stats.add_skipped()
                continue
            payload = _payload(testimonial_record.payload)
            payload.pop("evidence")
            status = PublicationStatus(payload.pop("status"))
            payload.pop("project_id", None)
            payload.pop("experience_id", None)
            testimonial_project = await self._reference(
                Project, testimonial_record.project_seed_key, projects, "project"
            )
            testimonial_experience = await self._reference(
                Experience,
                testimonial_record.experience_seed_key,
                experiences,
                "experience",
            )
            testimonial = Testimonial(
                **payload,
                project_id=testimonial_project.id if testimonial_project else None,
                experience_id=(testimonial_experience.id if testimonial_experience else None),
                is_approved=False,
                **self._provenance(testimonial_record.seed_key, source),
            )
            if testimonial_record.payload.evidence is not None:
                testimonial.evidence = _evidence(testimonial_record.payload.evidence)
            PublicationPolicy.apply(testimonial, status)
            self.repository.add(testimonial)
            stats.add_created()
        await self.repository.session.flush()
        return stats

    async def _simple_group(
        self,
        records: list[SeedRecord[Any]],
        model: type[ModelT],
        natural_field: str | None,
        source: SeedSource,
        stats: SeedStats,
    ) -> dict[str, ModelT]:
        resolved: dict[str, ModelT] = {}
        for seed_record in records:
            natural_value = getattr(seed_record.payload, natural_field) if natural_field else None
            existing_entity = await self._existing(
                model, seed_record.seed_key, natural_field, natural_value
            )
            if existing_entity:
                resolved[seed_record.seed_key] = existing_entity
                stats.add_skipped()
                continue
            payload = _payload(seed_record.payload)
            status = PublicationStatus(payload.pop("status"))
            entity = model(**payload, **self._provenance(seed_record.seed_key, source))
            PublicationPolicy.apply(entity, status)  # type: ignore[arg-type]
            self.repository.add(entity)
            resolved[seed_record.seed_key] = entity
            stats.add_created()
        await self.repository.session.flush()
        return resolved

    async def _existing(
        self,
        model: type[ModelT],
        seed_key: str,
        natural_field: str | None,
        natural_value: Any,
    ) -> ModelT | None:
        existing = await self.repository.get_by_seed_key(model, seed_key)
        if existing or not natural_field or natural_value is None:
            return existing
        return cast(
            ModelT | None,
            await self.repository.session.scalar(
                select(model).where(getattr(model, natural_field) == natural_value)
            ),
        )

    async def _reference(
        self,
        model: type[ModelT],
        seed_key: str | None,
        local: dict[str, ModelT],
        label: str,
    ) -> ModelT | None:
        if seed_key is None:
            return None
        return await self._required_reference(model, seed_key, local, label)

    async def _required_reference(
        self,
        model: type[ModelT],
        seed_key: str,
        local: dict[str, ModelT],
        label: str,
    ) -> ModelT:
        entity = local.get(seed_key) or await self.repository.get_by_seed_key(model, seed_key)
        if entity is None:
            raise ValidationError(f"Unknown {label} seed key '{seed_key}'.")
        return entity

    @staticmethod
    def _provenance(seed_key: str, source: SeedSource) -> dict[str, Any]:
        return {
            "seed_key": seed_key,
            "seed_source": source.value,
            "seeded_at": datetime.now(UTC),
        }
