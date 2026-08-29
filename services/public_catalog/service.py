"""Cross-domain catalog aggregation over public reader contracts."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, replace
from datetime import datetime
from urllib.parse import quote
from uuid import UUID

from packages.python.common.settings import Settings
from packages.python.common.urls import CanonicalUrlPolicy
from packages.python.contracts.features import FeatureFlagReader, FeatureResolution
from services.assistant.contracts import PublishedContentDocument, PublishedContentProvider
from services.content.contracts import ContentPublicReaderFactory
from services.content.schemas import PublicArticleRead, PublicArticleSummaryRead
from services.discovery.contracts import (
    DiscoveryBreadcrumb,
    DiscoveryContentProvider,
    DiscoveryDocument,
)
from services.identity.contracts import IdentityPublicReaderFactory
from services.identity.schemas import ProfileRead
from services.portfolio.contracts import PortfolioPublicReaderFactory
from services.portfolio.schemas import (
    CategoryRead,
    CertificationRead,
    EducationRead,
    ExperienceRead,
    PublicMetricRead,
    PublicProjectRead,
    PublicProjectSummaryRead,
    PublicSkillRead,
    PublicTestimonialRead,
    SectorRead,
)

_WORD_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#.-]{1,}", re.IGNORECASE)
_MARKDOWN_CONTROL = re.compile(r"[`*_>#|]+")
_SPACE = re.compile(r"\s+")
_STOP_WORDS = {
    "about",
    "and",
    "are",
    "can",
    "for",
    "from",
    "how",
    "the",
    "their",
    "this",
    "what",
    "with",
    "you",
}


@dataclass(frozen=True, slots=True)
class _PublicSnapshot:
    profile: ProfileRead | None
    categories: list[CategoryRead]
    sectors: list[SectorRead]
    skills: list[PublicSkillRead]
    experiences: list[ExperienceRead]
    education: list[EducationRead]
    certifications: list[CertificationRead]
    projects: list[PublicProjectSummaryRead | PublicProjectRead]
    metrics: list[PublicMetricRead]
    testimonials: list[PublicTestimonialRead]
    articles: list[PublicArticleSummaryRead | PublicArticleRead]


class CanonicalPublicContentProvider(
    PublishedContentProvider,
    DiscoveryContentProvider,
    FeatureFlagReader,
):
    """Map source-service public DTOs; never query another service's private model."""

    def __init__(
        self,
        *,
        identity_reader: IdentityPublicReaderFactory,
        portfolio_reader: PortfolioPublicReaderFactory,
        content_reader: ContentPublicReaderFactory,
        settings: Settings,
    ) -> None:
        self._identity_reader = identity_reader
        self._portfolio_reader = portfolio_reader
        self._content_reader = content_reader
        self._settings = settings
        self._canonical = CanonicalUrlPolicy(settings.public_base_url)

    async def is_enabled(self, key: str, *, default: bool) -> bool:
        return (await self.resolve_feature(key, default=default)).enabled

    async def resolve_feature(self, key: str, *, default: bool) -> FeatureResolution:
        async with self._content_reader() as content:
            return await content.resolve_feature(key, default=default)

    async def get_configuration(self, key: str) -> dict[str, object]:
        async with self._content_reader() as content:
            configuration = await content.active_feature_configuration(key)
        return configuration

    async def search_published(self, query: str, *, limit: int) -> list[PublishedContentDocument]:
        snapshot = await self._snapshot(
            limit=max(50, min(limit * 10, 200)),
            query=query,
        )
        terms = _query_terms(query)
        if not terms:
            return []
        ranked: list[PublishedContentDocument] = []
        for document in self._assistant_documents(snapshot):
            title = document.title.casefold()
            excerpt = document.excerpt.casefold()
            score = float(
                sum(4 for term in terms if term in title)
                + sum(excerpt.count(term) for term in terms)
            )
            if score > 0:
                ranked.append(replace(document, relevance=score))
        return sorted(ranked, key=lambda item: item.relevance, reverse=True)[:limit]

    async def list_for_discovery(self) -> list[DiscoveryDocument]:
        snapshot = await self._snapshot(limit=1000)
        return self._discovery_documents(snapshot)

    async def _snapshot(self, *, limit: int, query: str | None = None) -> _PublicSnapshot:
        async with (
            self._identity_reader() as identity,
            self._portfolio_reader() as portfolio,
            self._content_reader() as content,
        ):

            async def load_portfolio() -> tuple[
                list[CategoryRead],
                list[SectorRead],
                list[PublicSkillRead],
                list[ExperienceRead],
                list[EducationRead],
                list[CertificationRead],
                list[PublicProjectSummaryRead] | list[PublicProjectRead],
                list[PublicMetricRead],
                list[PublicTestimonialRead],
            ]:
                return (
                    await portfolio.list_public_categories(limit),
                    await portfolio.list_public_sectors(limit),
                    await portfolio.list_public_skills(limit),
                    await portfolio.list_public_experiences(limit),
                    await portfolio.list_public_education(limit),
                    await portfolio.list_public_certifications(limit),
                    (
                        await portfolio.search_public_projects(query, limit=limit)
                        if query
                        else await portfolio.list_public_projects(limit)
                    ),
                    await portfolio.list_public_metrics(limit),
                    await portfolio.list_public_testimonials(limit),
                )

            async def load_articles() -> list[PublicArticleSummaryRead | PublicArticleRead]:
                if query:
                    return list(await content.search_public_articles(query, limit=limit))
                return list(await content.list_public_articles(limit))

            profile, portfolio_values, articles = await asyncio.gather(
                identity.get_public_profile(),
                load_portfolio(),
                load_articles(),
            )
            (
                categories,
                sectors,
                skills,
                experiences,
                education,
                certifications,
                projects,
                metrics,
                testimonials,
            ) = portfolio_values
            project_documents: list[PublicProjectSummaryRead | PublicProjectRead] = list(projects)
        return _PublicSnapshot(
            profile=profile,
            categories=categories,
            sectors=sectors,
            skills=skills,
            experiences=experiences,
            education=education,
            certifications=certifications,
            projects=project_documents,
            metrics=metrics,
            testimonials=testimonials,
            articles=articles,
        )

    def _assistant_documents(self, snapshot: _PublicSnapshot) -> list[PublishedContentDocument]:
        documents: list[PublishedContentDocument] = []
        if snapshot.profile is not None:
            profile = snapshot.profile
            documents.append(
                PublishedContentDocument(
                    source_id=f"profile:{profile.id}",
                    content_type="profile",
                    title=f"{profile.full_name} — {profile.headline}",
                    excerpt=_plain_text(
                        " ".join(
                            part
                            for part in (
                                profile.headline,
                                profile.short_bio,
                                profile.long_bio,
                                profile.public_location,
                            )
                            if part
                        )
                    ),
                    canonical_url=self._canonical.build("/"),
                    published_at=profile.published_at,
                    is_indexable=not profile.noindex,
                )
            )
        for project in snapshot.projects:
            project_parts: list[str] = [project.summary]
            if isinstance(project, PublicProjectRead):
                project_parts.extend(
                    part
                    for part in (
                        project.description,
                        project.problem,
                        project.solution,
                        project.architecture,
                    )
                    if part
                )
                project_parts.extend(
                    project.features + project.decisions + project.challenges + project.outcomes
                )
            project_parts.extend(
                f"{metric.label}: {metric.value} {metric.unit or ''}. {metric.context}"
                for metric in project.metrics
            )
            documents.append(
                PublishedContentDocument(
                    source_id=f"project:{project.id}",
                    content_type="project",
                    title=project.title,
                    excerpt=_plain_text(" ".join(project_parts)),
                    canonical_url=self._canonical.build(f"/projects/{project.slug}"),
                    published_at=project.published_at,
                    is_indexable=not project.noindex,
                )
            )
        documents.extend(
            PublishedContentDocument(
                source_id=f"article:{article.id}",
                content_type="article",
                title=article.title,
                excerpt=_plain_text(
                    f"{article.excerpt} "
                    f"{article.body_markdown if isinstance(article, PublicArticleRead) else ''}"
                ),
                canonical_url=self._canonical.build(f"/writing/{article.slug}"),
                published_at=article.published_at,
                is_indexable=not article.noindex,
            )
            for article in snapshot.articles
        )
        documents.extend(self._portfolio_fact_documents(snapshot))
        return documents

    def _portfolio_fact_documents(
        self, snapshot: _PublicSnapshot
    ) -> list[PublishedContentDocument]:
        documents = [
            PublishedContentDocument(
                source_id=f"skill:{skill.id}",
                content_type="skill",
                title=skill.name,
                excerpt=_plain_text(
                    " ".join(
                        part
                        for part in (
                            skill.description,
                            skill.proficiency_label,
                            (
                                f"{skill.years_experience} years of experience"
                                if skill.years_experience is not None
                                else None
                            ),
                        )
                        if part
                    )
                ),
                canonical_url=self._canonical.build("/about"),
                published_at=skill.published_at,
                is_indexable=not skill.noindex,
            )
            for skill in snapshot.skills
        ]
        documents.extend(
            PublishedContentDocument(
                source_id=f"sector:{sector.id}",
                content_type="sector",
                title=sector.name,
                excerpt=_plain_text(sector.description),
                canonical_url=self._canonical.build(f"/sectors/{quote(sector.slug)}"),
                published_at=sector.published_at,
                is_indexable=not sector.noindex,
            )
            for sector in snapshot.sectors
        )
        documents.extend(
            PublishedContentDocument(
                source_id=f"experience:{experience.id}",
                content_type="experience",
                title=f"{experience.role} at {experience.organization}",
                excerpt=_plain_text(" ".join((experience.summary, *experience.achievements))),
                canonical_url=self._canonical.build("/work"),
                published_at=experience.published_at,
                is_indexable=not experience.noindex,
            )
            for experience in snapshot.experiences
        )
        project_paths = {
            project.id: f"/projects/{quote(project.slug)}" for project in snapshot.projects
        }
        documents.extend(
            _metric_document(metric, self._canonical, project_paths) for metric in snapshot.metrics
        )
        documents.extend(
            _testimonial_document(testimonial, self._canonical, project_paths)
            for testimonial in snapshot.testimonials
        )
        return documents

    def _discovery_documents(self, snapshot: _PublicSnapshot) -> list[DiscoveryDocument]:
        documents: list[DiscoveryDocument] = []
        profile = snapshot.profile
        if profile is not None:
            primary_portrait = next(
                (portrait for portrait in profile.portraits if portrait.is_primary),
                profile.portraits[0] if profile.portraits else None,
            )
            configured_verified = set(self._settings.verified_same_as_urls)
            public_social_urls = {str(link.url) for link in profile.social_links}
            documents.append(
                DiscoveryDocument(
                    source_id=f"profile:{profile.id}",
                    content_type="profile",
                    path="/",
                    title=f"{profile.full_name} — {profile.headline}",
                    description=profile.short_bio,
                    image_url=(
                        f"/api/v1/public/portraits/{primary_portrait.id}"
                        if primary_portrait
                        else None
                    ),
                    published_at=profile.published_at,
                    modified_at=profile.updated_at,
                    author_name=profile.full_name,
                    owner_headline=profile.headline,
                    verified_same_as_urls=tuple(
                        sorted(configured_verified.intersection(public_social_urls))
                    ),
                    noindex=profile.noindex,
                )
            )
        author_name = profile.full_name if profile else None
        for project in snapshot.projects:
            image_url = next(
                (
                    media.external_url or f"/api/v1/public/project-media/{media.id}"
                    for media in project.media
                    if media.is_visible and media.media_type.startswith("image/")
                ),
                None,
            )
            schema_type = {
                "software": "SoftwareSourceCode",
                "product": "Product",
                "case_study": "CreativeWork",
            }[project.nature.value]
            documents.append(
                DiscoveryDocument(
                    source_id=f"project:{project.id}",
                    content_type="project",
                    schema_type=schema_type,
                    path=f"/projects/{project.slug}",
                    title=project.seo_title or project.title,
                    description=project.seo_description or project.summary,
                    image_url=image_url,
                    published_at=project.published_at,
                    modified_at=project.updated_at,
                    author_name=author_name,
                    keywords=tuple(
                        dict.fromkeys(
                            [
                                *(skill.name for skill in project.skills),
                                *(sector.name for sector in project.sectors),
                            ]
                        )
                    ),
                    breadcrumbs=(DiscoveryBreadcrumb(label="Projects", path="/projects"),),
                    related_paths=tuple(
                        dict.fromkeys(
                            (
                                "/about",
                                "/achievements",
                                "/work",
                                "/sectors",
                                "/writing",
                                *(f"/sectors/{sector.slug}" for sector in project.sectors),
                            )
                        )
                    ),
                    noindex=project.noindex,
                )
            )
        documents.extend(
            DiscoveryDocument(
                source_id=f"article:{article.id}",
                content_type="article",
                path=f"/writing/{article.slug}",
                title=article.seo_title or article.title,
                description=article.seo_description or article.excerpt,
                image_url=(
                    f"/api/v1/public/media/{article.hero_media.id}" if article.hero_media else None
                ),
                published_at=article.published_at,
                modified_at=article.updated_at,
                author_name=author_name,
                keywords=tuple(article.topics),
                breadcrumbs=(DiscoveryBreadcrumb(label="Writing", path="/writing"),),
                related_paths=("/projects", "/about"),
                noindex=article.noindex,
            )
            for article in snapshot.articles
        )
        documents.extend(_sector_documents(snapshot, author_name))
        documents.extend(_collection_documents(snapshot, author_name))
        return documents


def _sector_documents(
    snapshot: _PublicSnapshot,
    author_name: str | None,
) -> list[DiscoveryDocument]:
    documents: list[DiscoveryDocument] = []
    for sector in snapshot.sectors:
        projects = [
            project
            for project in snapshot.projects
            if any(project_sector.id == sector.id for project_sector in project.sectors)
        ]
        skills = dict.fromkeys(skill.name for project in projects for skill in project.skills)
        modified_values = [sector.updated_at, *(project.updated_at for project in projects)]
        documents.append(
            DiscoveryDocument(
                source_id=f"sector:{sector.id}",
                content_type="sector",
                path=f"/sectors/{sector.slug}",
                title=sector.name,
                description=sector.description,
                modified_at=max(modified_values),
                published_at=sector.published_at,
                author_name=author_name,
                keywords=tuple(skills),
                breadcrumbs=(DiscoveryBreadcrumb(label="Sectors", path="/sectors"),),
                related_paths=tuple(
                    dict.fromkeys(
                        ("/projects", *(f"/projects/{project.slug}" for project in projects[:12]))
                    )
                ),
                noindex=sector.noindex,
            )
        )
    return documents


def _collection_documents(
    snapshot: _PublicSnapshot, author_name: str | None
) -> list[DiscoveryDocument]:
    definitions: list[tuple[str, str, str, list[str], list[datetime]]] = []
    if snapshot.projects:
        definitions.append(
            (
                "collection:projects",
                "/projects",
                "Projects",
                [project.summary for project in snapshot.projects[:8]],
                [project.updated_at for project in snapshot.projects],
            )
        )
    if snapshot.articles:
        definitions.append(
            (
                "collection:articles",
                "/writing",
                "Writing",
                [article.excerpt for article in snapshot.articles[:8]],
                [article.updated_at for article in snapshot.articles],
            )
        )
    if snapshot.sectors:
        definitions.append(
            (
                "collection:sectors",
                "/sectors",
                "Sectors",
                [sector.description for sector in snapshot.sectors[:12]],
                [sector.updated_at for sector in snapshot.sectors],
            )
        )
    about_parts = [
        *(item.description or item.name for item in snapshot.skills),
        *(item.summary for item in snapshot.experiences),
        *(item.summary or item.credential for item in snapshot.education),
        *(item.description or f"{item.name}, {item.issuer}" for item in snapshot.certifications),
        *(item.description for item in snapshot.categories),
    ]
    about_updates = [
        *(item.updated_at for item in snapshot.skills),
        *(item.updated_at for item in snapshot.experiences),
        *(item.updated_at for item in snapshot.education),
        *(item.updated_at for item in snapshot.certifications),
        *(item.updated_at for item in snapshot.categories),
    ]
    if about_parts:
        definitions.append(("collection:about", "/about", "About", about_parts[:20], about_updates))
    if snapshot.experiences:
        definitions.append(
            (
                "collection:work",
                "/work",
                "Work",
                [
                    _plain_text(" ".join((item.summary, *item.achievements)))
                    for item in snapshot.experiences[:12]
                ],
                [item.updated_at for item in snapshot.experiences],
            )
        )
    publication_articles = [
        article
        for article in snapshot.articles
        if any(topic.casefold() == "publication" for topic in article.topics)
    ]
    achievement_parts = [
        *(item.description or f"{item.name}, {item.issuer}" for item in snapshot.certifications),
        *(achievement for item in snapshot.experiences for achievement in item.achievements),
        *(achievement for item in snapshot.education for achievement in item.achievements),
        *(article.excerpt for article in publication_articles),
    ]
    achievement_updates = [
        *(item.updated_at for item in snapshot.certifications),
        *(item.updated_at for item in snapshot.experiences),
        *(item.updated_at for item in snapshot.education),
        *(item.updated_at for item in publication_articles),
    ]
    if achievement_parts:
        definitions.append(
            (
                "collection:achievements",
                "/achievements",
                "Achievements",
                achievement_parts[:24],
                achievement_updates,
            )
        )
    open_source_projects = [project for project in snapshot.projects if project.is_open_source]
    if open_source_projects:
        definitions.append(
            (
                "collection:open-source",
                "/open-source",
                "Open Source",
                [project.summary for project in open_source_projects[:12]],
                [project.updated_at for project in open_source_projects],
            )
        )
    return [
        DiscoveryDocument(
            source_id=source_id,
            content_type="collection",
            path=path,
            title=title,
            description=_plain_text(" ".join(parts))[:320],
            modified_at=max(updated_values) if updated_values else None,
            author_name=author_name,
            breadcrumbs=(DiscoveryBreadcrumb(label=title, path=path),),
        )
        for source_id, path, title, parts, updated_values in definitions
    ]


def _metric_document(
    metric: PublicMetricRead,
    canonical: CanonicalUrlPolicy,
    project_paths: dict[UUID, str],
) -> PublishedContentDocument:
    return PublishedContentDocument(
        source_id=f"metric:{metric.id}",
        content_type="verified_metric",
        title=metric.label,
        excerpt=_plain_text(f"{metric.value} {metric.unit or ''}. {metric.context}"),
        canonical_url=canonical.build(
            (project_paths.get(metric.project_id) if metric.project_id is not None else None)
            or ("/work" if metric.experience_id else "/")
        ),
        published_at=metric.published_at,
        is_indexable=not metric.noindex,
    )


def _testimonial_document(
    testimonial: PublicTestimonialRead,
    canonical: CanonicalUrlPolicy,
    project_paths: dict[UUID, str],
) -> PublishedContentDocument:
    attribution = " ".join(
        part
        for part in (
            testimonial.attribution_name,
            testimonial.attribution_title,
            testimonial.attribution_organization,
        )
        if part
    )
    return PublishedContentDocument(
        source_id=f"testimonial:{testimonial.id}",
        content_type="approved_testimonial",
        title=f"Testimonial from {testimonial.attribution_name}",
        excerpt=_plain_text(f"{testimonial.quote} — {attribution}"),
        canonical_url=canonical.build(
            (
                project_paths.get(testimonial.project_id)
                if testimonial.project_id is not None
                else None
            )
            or ("/work" if testimonial.experience_id else "/")
        ),
        published_at=testimonial.published_at,
        is_indexable=not testimonial.noindex,
    )


def _query_terms(query: str) -> set[str]:
    return {
        term.casefold()
        for term in _WORD_PATTERN.findall(query)
        if term.casefold() not in _STOP_WORDS
    }


def _plain_text(value: str) -> str:
    return _SPACE.sub(" ", _MARKDOWN_CONTROL.sub(" ", value)).strip()[:12_000]
