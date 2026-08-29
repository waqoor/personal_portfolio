from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypeVar, cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, load_only, selectinload

from packages.python.common.models import Base, PublicationStatus
from services.portfolio.models import (
    Certification,
    Education,
    EvidenceKind,
    Experience,
    ImpactMetric,
    PortfolioApprovalEvent,
    PortfolioEvidence,
    ProfessionalCategory,
    Project,
    ProjectMedia,
    RepositoryMetadataSnapshot,
    Sector,
    Skill,
    Testimonial,
    project_sectors,
    project_skills,
)

PortfolioModel = TypeVar("PortfolioModel", bound=Base)


class PortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _project_options() -> tuple[Any, ...]:
        return (
            joinedload(Project.category),
            selectinload(Project.skills),
            selectinload(Project.sectors),
            selectinload(Project.media),
            selectinload(Project.metrics).joinedload(ImpactMetric.experience),
            selectinload(Project.metrics)
            .joinedload(ImpactMetric.evidence)
            .joinedload(PortfolioEvidence.managed_media),
            selectinload(Project.testimonials).joinedload(Testimonial.experience),
            selectinload(Project.testimonials)
            .joinedload(Testimonial.evidence)
            .joinedload(PortfolioEvidence.managed_media),
            joinedload(Project.repository_metadata),
        )

    @staticmethod
    def _project_summary_options() -> tuple[Any, ...]:
        """Load only card fields and relationships for collection responses."""

        return (
            load_only(
                Project.id,
                Project.created_at,
                Project.updated_at,
                Project.status,
                Project.is_visible,
                Project.noindex,
                Project.published_at,
                Project.archived_at,
                Project.category_id,
                Project.title,
                Project.slug,
                Project.summary,
                Project.role,
                Project.start_date,
                Project.end_date,
                Project.links,
                Project.repository_url,
                Project.live_url,
                Project.is_open_source,
                Project.repository_metadata_refresh_enabled,
                Project.nature,
                Project.featured_rank,
                Project.seo_title,
                Project.seo_description,
            ),
            joinedload(Project.category),
            joinedload(Project.repository_metadata),
            selectinload(Project.skills),
            selectinload(Project.sectors),
            selectinload(Project.media),
            selectinload(Project.metrics).joinedload(ImpactMetric.experience),
            selectinload(Project.metrics)
            .joinedload(ImpactMetric.evidence)
            .joinedload(PortfolioEvidence.managed_media),
        )

    @staticmethod
    def _experience_options() -> tuple[Any, ...]:
        return (
            selectinload(Experience.skills),
            selectinload(Experience.sectors),
            selectinload(Experience.projects),
        )

    async def get(self, model: type[PortfolioModel], entity_id: UUID) -> PortfolioModel | None:
        if model is Project:
            return cast(
                PortfolioModel | None,
                await self.session.scalar(
                    select(Project).where(Project.id == entity_id).options(*self._project_options())
                ),
            )
        if model is Experience:
            return cast(
                PortfolioModel | None,
                await self.session.scalar(
                    select(Experience)
                    .where(Experience.id == entity_id)
                    .options(*self._experience_options())
                ),
            )
        if model is ImpactMetric:
            return cast(
                PortfolioModel | None,
                await self.session.scalar(
                    select(ImpactMetric)
                    .where(ImpactMetric.id == entity_id)
                    .options(
                        joinedload(ImpactMetric.project),
                        joinedload(ImpactMetric.experience),
                        joinedload(ImpactMetric.evidence).joinedload(
                            PortfolioEvidence.managed_media
                        ),
                    )
                ),
            )
        if model is Testimonial:
            return cast(
                PortfolioModel | None,
                await self.session.scalar(
                    select(Testimonial)
                    .where(Testimonial.id == entity_id)
                    .options(
                        joinedload(Testimonial.project),
                        joinedload(Testimonial.experience),
                        joinedload(Testimonial.evidence).joinedload(
                            PortfolioEvidence.managed_media
                        ),
                    )
                ),
            )
        return await self.session.get(model, entity_id)

    async def get_by_seed_key(
        self, model: type[PortfolioModel], seed_key: str
    ) -> PortfolioModel | None:
        return cast(
            PortfolioModel | None,
            await self.session.scalar(
                select(model).where(model.seed_key == seed_key)  # type: ignore[attr-defined]
            ),
        )

    async def get_many(self, model: type[PortfolioModel], ids: list[UUID]) -> list[PortfolioModel]:
        if not ids:
            return []
        result = await self.session.scalars(select(model).where(model.id.in_(set(ids))))  # type: ignore[attr-defined]
        return list(result.unique().all())

    async def get_project_for_update(self, entity_id: UUID) -> Project | None:
        return cast(
            Project | None,
            await self.session.scalar(
                select(Project)
                .where(Project.id == entity_id)
                .options(*self._project_options())
                .with_for_update(of=Project)
            ),
        )

    async def get_repository_snapshot_for_update(
        self, project_id: UUID
    ) -> RepositoryMetadataSnapshot | None:
        return cast(
            RepositoryMetadataSnapshot | None,
            await self.session.scalar(
                select(RepositoryMetadataSnapshot)
                .where(RepositoryMetadataSnapshot.project_id == project_id)
                .with_for_update()
            ),
        )

    def add_repository_snapshot(
        self, snapshot: RepositoryMetadataSnapshot
    ) -> RepositoryMetadataSnapshot:
        self.session.add(snapshot)
        return snapshot

    async def list_featured_projects_for_update(
        self, requested_ids: Sequence[UUID] = ()
    ) -> Sequence[Project]:
        statement = select(Project).where(
            or_(
                and_(
                    Project.featured_rank.is_not(None),
                    Project.status == PublicationStatus.PUBLISHED,
                    Project.is_visible.is_(True),
                    Project.archived_at.is_(None),
                ),
                Project.id.in_(requested_ids),
            )
        )
        return (
            (
                await self.session.scalars(
                    statement.options(*self._project_options())
                    .order_by(Project.featured_rank.asc().nulls_last(), Project.id)
                    .with_for_update(of=Project)
                )
            )
            .unique()
            .all()
        )

    async def list_active_featured_projects(self, *, limit: int) -> Sequence[Project]:
        """Return the current public slot occupants with the full admin projection."""

        statement = (
            select(Project)
            .where(
                Project.featured_rank.is_not(None),
                Project.status == PublicationStatus.PUBLISHED,
                Project.is_visible.is_(True),
                Project.archived_at.is_(None),
            )
            .options(*self._project_options())
            .order_by(Project.featured_rank, Project.id)
            .limit(limit)
        )
        return (await self.session.scalars(statement)).unique().all()

    async def get_public_project_by_slug(self, slug: str) -> Project | None:
        return cast(
            Project | None,
            await self.session.scalar(
                select(Project)
                .where(
                    Project.slug == slug,
                    Project.status == PublicationStatus.PUBLISHED,
                    Project.is_visible.is_(True),
                    Project.archived_at.is_(None),
                )
                .options(*self._project_options())
            ),
        )

    async def get_public_sector_by_slug(self, slug: str) -> Sector | None:
        return cast(
            Sector | None,
            await self.session.scalar(
                select(Sector).where(
                    Sector.slug == slug,
                    Sector.status == PublicationStatus.PUBLISHED,
                    Sector.is_visible.is_(True),
                    Sector.archived_at.is_(None),
                )
            ),
        )

    async def list_related_public_projects(
        self, project: Project, *, limit: int = 3
    ) -> Sequence[Project]:
        """Rank public candidates by shared category, sectors, then skills."""

        predicates: list[Any] = []
        if project.category_id is not None:
            predicates.append(Project.category_id == project.category_id)
        sector_ids = {sector.id for sector in project.sectors}
        if sector_ids:
            predicates.append(Project.sectors.any(Sector.id.in_(sector_ids)))
        skill_ids = {skill.id for skill in project.skills}
        if skill_ids:
            predicates.append(Project.skills.any(Skill.id.in_(skill_ids)))
        if not predicates:
            return []

        statement = (
            select(Project)
            .where(
                Project.id != project.id,
                Project.status == PublicationStatus.PUBLISHED,
                Project.is_visible.is_(True),
                Project.archived_at.is_(None),
                Project.noindex.is_(False),
                or_(*predicates),
            )
            .options(*self._project_summary_options())
            .order_by(
                Project.featured_rank.asc().nulls_last(),
                Project.start_date.desc().nulls_last(),
                Project.created_at.desc(),
                Project.id,
            )
            .limit(max(limit * 10, 30))
        )
        candidates = (await self.session.scalars(statement)).unique().all()

        def score(candidate: Project) -> tuple[int, int, str]:
            similarity = (
                (4 if candidate.category_id == project.category_id else 0)
                + 3 * len(sector_ids.intersection(item.id for item in candidate.sectors))
                + 2 * len(skill_ids.intersection(item.id for item in candidate.skills))
            )
            return (-similarity, candidate.featured_rank or 1_000_000, candidate.slug)

        return sorted(candidates, key=score)[:limit]

    def add(self, entity: PortfolioModel) -> PortfolioModel:
        self.session.add(entity)
        return entity

    async def flush(self) -> None:
        await self.session.flush()

    async def delete(self, entity: PortfolioModel) -> None:
        await self.session.delete(entity)

    async def list_entities(
        self,
        model: type[PortfolioModel],
        *,
        limit: int,
        offset: int = 0,
        public: bool = False,
        approved_only: bool = False,
        featured_only: bool = False,
        search: str | None = None,
        status: PublicationStatus | None = None,
        open_source: bool | None = None,
        approved: bool | None = None,
    ) -> tuple[Sequence[PortfolioModel], int]:
        statement = select(model)
        if public:
            statement = statement.where(
                model.status == PublicationStatus.PUBLISHED,  # type: ignore[attr-defined]
                model.is_visible.is_(True),  # type: ignore[attr-defined]
                model.archived_at.is_(None),  # type: ignore[attr-defined]
            )
        if approved_only:
            statement = statement.where(model.is_approved.is_(True))  # type: ignore[attr-defined]
        if featured_only:
            statement = statement.where(Project.featured_rank.is_not(None))
        if status is not None:
            statement = statement.where(model.status == status)  # type: ignore[attr-defined]
        if open_source is not None and model is Project:
            statement = statement.where(Project.is_open_source.is_(open_source))
        if approved is not None and model in {ImpactMetric, Testimonial}:
            statement = statement.where(model.is_approved.is_(approved))  # type: ignore[attr-defined]
        if search:
            columns: dict[type[Base], tuple[Any, ...]] = {
                ProfessionalCategory: (
                    ProfessionalCategory.name,
                    ProfessionalCategory.slug,
                    ProfessionalCategory.description,
                ),
                Sector: (Sector.name, Sector.slug, Sector.description),
                Skill: (Skill.name, Skill.slug, Skill.description),
                Experience: (Experience.organization, Experience.role, Experience.summary),
                Education: (Education.institution, Education.credential, Education.summary),
                Certification: (
                    Certification.name,
                    Certification.issuer,
                    Certification.description,
                ),
                Project: (Project.title, Project.slug, Project.summary, Project.description),
                ImpactMetric: (ImpactMetric.label, ImpactMetric.value, ImpactMetric.context),
                Testimonial: (
                    Testimonial.quote,
                    Testimonial.attribution_name,
                    Testimonial.attribution_organization,
                ),
            }
            selected = columns.get(model, ())
            if selected:
                pattern = f"%{search.strip()}%"
                statement = statement.where(or_(*(column.ilike(pattern) for column in selected)))
        if model is Project:
            project_options = self._project_summary_options() if public else self._project_options()
            statement = statement.options(*project_options).order_by(
                Project.featured_rank.asc().nulls_last(), Project.start_date.desc().nulls_last()
            )
        elif model is Experience:
            statement = statement.options(*self._experience_options()).order_by(
                Experience.sort_order, Experience.start_date.desc()
            )
        elif model is ImpactMetric:
            statement = statement.options(
                joinedload(ImpactMetric.project),
                joinedload(ImpactMetric.experience),
                joinedload(ImpactMetric.evidence).joinedload(PortfolioEvidence.managed_media),
            ).order_by(ImpactMetric.sort_order, ImpactMetric.created_at)
        elif model is Testimonial:
            statement = statement.options(
                joinedload(Testimonial.project),
                joinedload(Testimonial.experience),
                joinedload(Testimonial.evidence).joinedload(PortfolioEvidence.managed_media),
            ).order_by(Testimonial.sort_order, Testimonial.created_at)
        elif model in {Education, Certification}:
            statement = statement.order_by(model.sort_order, model.created_at.desc())  # type: ignore[attr-defined]
        else:
            statement = statement.order_by(model.sort_order, model.created_at)  # type: ignore[attr-defined]
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total = int((await self.session.scalar(count_statement)) or 0)
        values = (await self.session.scalars(statement.limit(limit).offset(offset))).unique().all()
        return values, total

    async def list_public_projects_page(
        self,
        *,
        limit: int,
        offset: int,
        category: str | None = None,
        sector: str | None = None,
        search: str | None = None,
        open_source: bool | None = None,
    ) -> tuple[Sequence[Project], int]:
        statement = select(Project).where(
            Project.status == PublicationStatus.PUBLISHED,
            Project.is_visible.is_(True),
            Project.archived_at.is_(None),
        )
        if category:
            statement = statement.where(Project.category.has(ProfessionalCategory.slug == category))
        if sector:
            statement = statement.where(Project.sectors.any(Sector.slug == sector))
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(Project.title.ilike(pattern), Project.summary.ilike(pattern))
            )
        if open_source is not None:
            statement = statement.where(Project.is_open_source.is_(open_source))
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total = int((await self.session.scalar(count_statement)) or 0)
        statement = statement.options(*self._project_summary_options()).order_by(
            Project.featured_rank.asc().nulls_last(),
            Project.start_date.desc().nulls_last(),
            Project.created_at.desc(),
        )
        items = (await self.session.scalars(statement.limit(limit).offset(offset))).unique().all()
        return items, total

    async def search_public_project_details(self, query: str, *, limit: int) -> Sequence[Project]:
        pattern = f"%{query.strip()}%"
        statement = (
            select(Project)
            .where(
                Project.status == PublicationStatus.PUBLISHED,
                Project.is_visible.is_(True),
                Project.archived_at.is_(None),
                Project.noindex.is_(False),
                or_(
                    Project.title.ilike(pattern),
                    Project.summary.ilike(pattern),
                    Project.description.ilike(pattern),
                    Project.problem.ilike(pattern),
                    Project.solution.ilike(pattern),
                    Project.architecture.ilike(pattern),
                ),
            )
            .options(*self._project_options())
            .order_by(
                Project.featured_rank.asc().nulls_last(),
                Project.start_date.desc().nulls_last(),
                Project.created_at.desc(),
            )
            .limit(limit)
        )
        return (await self.session.scalars(statement)).unique().all()

    async def list_public_sectors_with_project_counts(
        self, *, limit: int
    ) -> list[tuple[Sector, int]]:
        published_projects = (
            select(func.count())
            .select_from(project_sectors.join(Project, Project.id == project_sectors.c.project_id))
            .where(
                project_sectors.c.sector_id == Sector.id,
                Project.status == PublicationStatus.PUBLISHED,
                Project.is_visible.is_(True),
                Project.archived_at.is_(None),
            )
            .correlate(Sector)
            .scalar_subquery()
        )
        statement = (
            select(Sector, published_projects.label("project_count"))
            .where(
                Sector.status == PublicationStatus.PUBLISHED,
                Sector.is_visible.is_(True),
                Sector.archived_at.is_(None),
            )
            .order_by(Sector.sort_order, Sector.created_at)
            .limit(limit)
        )
        rows = (await self.session.execute(statement)).all()
        return [(sector, int(project_count)) for sector, project_count in rows]

    async def list_public_skills_with_project_counts(
        self, *, limit: int
    ) -> list[tuple[Skill, int]]:
        published_projects = (
            select(func.count())
            .select_from(project_skills.join(Project, Project.id == project_skills.c.project_id))
            .where(
                project_skills.c.skill_id == Skill.id,
                Project.status == PublicationStatus.PUBLISHED,
                Project.is_visible.is_(True),
                Project.archived_at.is_(None),
            )
            .correlate(Skill)
            .scalar_subquery()
        )
        statement = (
            select(Skill, published_projects.label("project_count"))
            .where(
                Skill.status == PublicationStatus.PUBLISHED,
                Skill.is_visible.is_(True),
                Skill.archived_at.is_(None),
            )
            .order_by(Skill.sort_order, Skill.created_at)
            .limit(limit)
        )
        rows = (await self.session.execute(statement)).all()
        return [(skill, int(project_count)) for skill, project_count in rows]

    async def list_public_approved_evidence_subjects(
        self,
        model: type[ImpactMetric] | type[Testimonial],
        *,
        limit: int,
    ) -> Sequence[ImpactMetric | Testimonial]:
        """Return approved subjects only when every populated parent is publishable."""

        statement = (
            select(model)
            .where(
                model.status == PublicationStatus.PUBLISHED,
                model.is_visible.is_(True),
                model.archived_at.is_(None),
                model.noindex.is_(False),
                model.is_approved.is_(True),
                model.evidence.has(
                    and_(
                        PortfolioEvidence.archived_at.is_(None),
                        or_(
                            PortfolioEvidence.kind != EvidenceKind.MANAGED_MEDIA,
                            PortfolioEvidence.managed_media.has(ProjectMedia.is_visible.is_(True)),
                        ),
                    )
                ),
                or_(
                    model.project_id.is_(None),
                    model.project.has(
                        and_(
                            Project.status == PublicationStatus.PUBLISHED,
                            Project.is_visible.is_(True),
                            Project.archived_at.is_(None),
                            Project.noindex.is_(False),
                        )
                    ),
                ),
                or_(
                    model.experience_id.is_(None),
                    model.experience.has(
                        and_(
                            Experience.status == PublicationStatus.PUBLISHED,
                            Experience.is_visible.is_(True),
                            Experience.archived_at.is_(None),
                            Experience.noindex.is_(False),
                        )
                    ),
                ),
            )
            .options(
                joinedload(model.project),
                joinedload(model.experience),
                joinedload(model.evidence).joinedload(PortfolioEvidence.managed_media),
            )
            .order_by(model.sort_order, model.created_at)
            .limit(limit)
        )
        return cast(
            Sequence[ImpactMetric | Testimonial],
            (await self.session.scalars(statement)).unique().all(),
        )

    async def get_project_media(self, media_id: UUID) -> ProjectMedia | None:
        return await self.session.get(ProjectMedia, media_id)

    async def list_active_project_media(
        self, *, limit: int, offset: int, search: str | None = None
    ) -> tuple[Sequence[ProjectMedia], int]:
        statement = select(ProjectMedia).where(
            ProjectMedia.is_visible.is_(True), ProjectMedia.storage_key.is_not(None)
        )
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.join(Project, Project.id == ProjectMedia.project_id).where(
                or_(
                    ProjectMedia.original_filename.ilike(pattern),
                    ProjectMedia.alt_text.ilike(pattern),
                    ProjectMedia.caption.ilike(pattern),
                    Project.title.ilike(pattern),
                )
            )
        total = int(
            (
                await self.session.scalar(
                    select(func.count()).select_from(statement.order_by(None).subquery())
                )
            )
            or 0
        )
        values = (
            await self.session.scalars(
                statement.order_by(ProjectMedia.updated_at.desc(), ProjectMedia.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return values, total

    async def list_evidence_for_media_for_update(
        self, media_id: UUID
    ) -> Sequence[PortfolioEvidence]:
        return (
            (
                await self.session.scalars(
                    select(PortfolioEvidence)
                    .where(PortfolioEvidence.managed_media_id == media_id)
                    .options(
                        joinedload(PortfolioEvidence.metric),
                        joinedload(PortfolioEvidence.testimonial),
                    )
                    .with_for_update(of=PortfolioEvidence)
                )
            )
            .unique()
            .all()
        )

    async def get_public_project_media(self, media_id: UUID) -> ProjectMedia | None:
        return cast(
            ProjectMedia | None,
            await self.session.scalar(
                select(ProjectMedia)
                .join(Project, Project.id == ProjectMedia.project_id)
                .where(
                    ProjectMedia.id == media_id,
                    ProjectMedia.is_visible.is_(True),
                    Project.status == PublicationStatus.PUBLISHED,
                    Project.is_visible.is_(True),
                    Project.archived_at.is_(None),
                )
            ),
        )

    async def get_metric(self, metric_id: UUID) -> ImpactMetric | None:
        return await self.session.get(ImpactMetric, metric_id)

    async def get_metric_for_update(self, metric_id: UUID) -> ImpactMetric | None:
        return cast(
            ImpactMetric | None,
            await self.session.scalar(
                select(ImpactMetric)
                .where(ImpactMetric.id == metric_id)
                .options(
                    joinedload(ImpactMetric.project),
                    joinedload(ImpactMetric.experience),
                    joinedload(ImpactMetric.evidence).joinedload(PortfolioEvidence.managed_media),
                )
                .with_for_update(of=ImpactMetric)
            ),
        )

    async def get_testimonial(self, testimonial_id: UUID) -> Testimonial | None:
        return await self.session.get(Testimonial, testimonial_id)

    async def get_testimonial_for_update(self, testimonial_id: UUID) -> Testimonial | None:
        return cast(
            Testimonial | None,
            await self.session.scalar(
                select(Testimonial)
                .where(Testimonial.id == testimonial_id)
                .options(
                    joinedload(Testimonial.project),
                    joinedload(Testimonial.experience),
                    joinedload(Testimonial.evidence).joinedload(PortfolioEvidence.managed_media),
                )
                .with_for_update(of=Testimonial)
            ),
        )

    def add_evidence(self, evidence: PortfolioEvidence) -> PortfolioEvidence:
        self.session.add(evidence)
        return evidence

    def add_approval_event(self, event: PortfolioApprovalEvent) -> PortfolioApprovalEvent:
        self.session.add(event)
        return event
