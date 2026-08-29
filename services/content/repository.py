from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypeVar, cast
from uuid import UUID

from sqlalchemy import cast as sa_cast
from sqlalchemy import exists, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, load_only

from packages.python.common.models import Base, PublicationStatus
from services.content.models import (
    Article,
    FeatureSetting,
    HomepageSection,
    MediaAsset,
    NavigationItem,
)

ContentModel = TypeVar("ContentModel", bound=Base)


class ContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, model: type[ContentModel], entity_id: UUID) -> ContentModel | None:
        if model is Article:
            return cast(
                ContentModel | None,
                await self.session.scalar(
                    select(Article)
                    .where(Article.id == entity_id)
                    .options(joinedload(Article.hero_media))
                ),
            )
        return await self.session.get(model, entity_id)

    async def get_by_seed_key(
        self, model: type[ContentModel], seed_key: str
    ) -> ContentModel | None:
        return cast(
            ContentModel | None,
            await self.session.scalar(
                select(model).where(model.seed_key == seed_key)  # type: ignore[attr-defined]
            ),
        )

    def add(self, entity: ContentModel) -> ContentModel:
        self.session.add(entity)
        return entity

    @staticmethod
    def _article_summary_fields() -> Any:
        return load_only(
            Article.id,
            Article.created_at,
            Article.updated_at,
            Article.status,
            Article.is_visible,
            Article.noindex,
            Article.published_at,
            Article.archived_at,
            Article.hero_media_id,
            Article.title,
            Article.slug,
            Article.excerpt,
            Article.topics,
            Article.reading_minutes,
            Article.seo_title,
            Article.seo_description,
        )

    async def flush(self) -> None:
        await self.session.flush()

    async def get_public_article_by_slug(self, slug: str) -> Article | None:
        return cast(
            Article | None,
            await self.session.scalar(
                select(Article)
                .where(
                    Article.slug == slug,
                    Article.status == PublicationStatus.PUBLISHED,
                    Article.is_visible.is_(True),
                    Article.archived_at.is_(None),
                )
                .options(joinedload(Article.hero_media))
            ),
        )

    async def list_related_public_articles(
        self, article: Article, *, limit: int = 3
    ) -> Sequence[Article]:
        if not article.topics:
            return []
        statement = select(Article).where(
            Article.id != article.id,
            Article.status == PublicationStatus.PUBLISHED,
            Article.is_visible.is_(True),
            Article.archived_at.is_(None),
            Article.noindex.is_(False),
        )
        if self.session.get_bind().dialect.name == "postgresql":
            statement = statement.where(
                or_(*(sa_cast(Article.topics, JSONB).contains([topic]) for topic in article.topics))
            )
        else:
            values = func.json_each(Article.topics).table_valued("key", "value")
            statement = statement.where(
                exists(select(1).select_from(values).where(values.c.value.in_(article.topics)))
            )
        statement = (
            statement.options(self._article_summary_fields(), joinedload(Article.hero_media))
            .order_by(Article.published_at.desc(), Article.created_at.desc(), Article.slug)
            .limit(max(limit * 10, 30))
        )
        candidates = (await self.session.scalars(statement)).unique().all()
        topics = set(article.topics)
        return sorted(
            candidates,
            key=lambda item: (
                -len(topics.intersection(item.topics)),
                -(item.published_at or item.created_at).timestamp(),
                item.slug,
            ),
        )[:limit]

    async def get_feature_by_key(self, key: str) -> FeatureSetting | None:
        return cast(
            FeatureSetting | None,
            await self.session.scalar(select(FeatureSetting).where(FeatureSetting.key == key)),
        )

    async def list_entities(
        self,
        model: type[ContentModel],
        *,
        limit: int,
        offset: int = 0,
        public: bool = False,
        search: str | None = None,
        status: PublicationStatus | None = None,
    ) -> tuple[Sequence[ContentModel], int]:
        statement = select(model)
        if public:
            statement = statement.where(
                model.status == PublicationStatus.PUBLISHED,  # type: ignore[attr-defined]
                model.is_visible.is_(True),  # type: ignore[attr-defined]
                model.archived_at.is_(None),  # type: ignore[attr-defined]
            )
        if status is not None and model is not FeatureSetting:
            statement = statement.where(model.status == status)  # type: ignore[attr-defined]
        if search:
            columns: dict[type[Base], tuple[Any, ...]] = {
                MediaAsset: (
                    MediaAsset.original_filename,
                    MediaAsset.alt_text,
                    MediaAsset.caption,
                ),
                Article: (Article.title, Article.slug, Article.excerpt),
                HomepageSection: (HomepageSection.title, HomepageSection.variant),
                NavigationItem: (NavigationItem.label, NavigationItem.href),
                FeatureSetting: (FeatureSetting.key, FeatureSetting.description),
            }
            selected = columns.get(model, ())
            if selected:
                pattern = f"%{search.strip()}%"
                statement = statement.where(or_(*(column.ilike(pattern) for column in selected)))
        if model is Article:
            if public:
                statement = statement.options(
                    self._article_summary_fields(), joinedload(Article.hero_media)
                )
            else:
                statement = statement.options(joinedload(Article.hero_media))
            statement = statement.order_by(Article.published_at.desc(), Article.created_at.desc())
        elif model is HomepageSection:
            statement = statement.order_by(HomepageSection.position)
        elif model is NavigationItem:
            statement = statement.order_by(NavigationItem.location, NavigationItem.sort_order)
        else:
            statement = statement.order_by(model.created_at.desc())  # type: ignore[attr-defined]
        count = int(
            (
                await self.session.scalar(
                    select(func.count()).select_from(statement.order_by(None).subquery())
                )
            )
            or 0
        )
        items = (await self.session.scalars(statement.limit(limit).offset(offset))).unique().all()
        return items, count

    async def list_public_sections(self) -> Sequence[HomepageSection]:
        return (
            await self.session.scalars(
                select(HomepageSection)
                .where(
                    HomepageSection.status == PublicationStatus.PUBLISHED,
                    HomepageSection.is_visible.is_(True),
                    HomepageSection.archived_at.is_(None),
                    HomepageSection.enabled.is_(True),
                )
                .order_by(HomepageSection.position)
            )
        ).all()

    async def list_public_articles_page(
        self,
        *,
        limit: int,
        offset: int,
        topic: str | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[Article], int]:
        statement = (
            select(Article)
            .where(
                Article.status == PublicationStatus.PUBLISHED,
                Article.is_visible.is_(True),
                Article.archived_at.is_(None),
            )
            .options(self._article_summary_fields(), joinedload(Article.hero_media))
        )
        if topic:
            if self.session.get_bind().dialect.name == "postgresql":
                # ``json_type()`` is portable and therefore exposes the generic
                # JSON comparator. Cast explicitly so PostgreSQL uses JSONB's
                # containment operator instead of the generic LIKE fallback.
                statement = statement.where(sa_cast(Article.topics, JSONB).contains([topic]))
            else:
                values = func.json_each(Article.topics).table_valued("key", "value")
                statement = statement.where(
                    exists(select(1).select_from(values).where(values.c.value == topic))
                )
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(Article.title.ilike(pattern), Article.excerpt.ilike(pattern))
            )
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total = int((await self.session.scalar(count_statement)) or 0)
        statement = statement.order_by(Article.published_at.desc(), Article.created_at.desc())
        items = (await self.session.scalars(statement.limit(limit).offset(offset))).all()
        return items, total

    async def search_public_articles(self, query: str, *, limit: int) -> Sequence[Article]:
        pattern = f"%{query.strip()}%"
        statement = (
            select(Article)
            .where(
                Article.status == PublicationStatus.PUBLISHED,
                Article.is_visible.is_(True),
                Article.archived_at.is_(None),
                Article.noindex.is_(False),
                or_(
                    Article.title.ilike(pattern),
                    Article.excerpt.ilike(pattern),
                    Article.body_markdown.ilike(pattern),
                ),
            )
            .options(joinedload(Article.hero_media))
            .order_by(Article.published_at.desc(), Article.created_at.desc())
            .limit(limit)
        )
        return (await self.session.scalars(statement)).all()

    async def list_public_article_topics(self) -> list[str]:
        topic_lists = await self.session.scalars(
            select(Article.topics).where(
                Article.status == PublicationStatus.PUBLISHED,
                Article.is_visible.is_(True),
                Article.archived_at.is_(None),
            )
        )
        return sorted({topic for topics in topic_lists for topic in topics})

    async def list_all_sections(self) -> Sequence[HomepageSection]:
        return (
            await self.session.scalars(select(HomepageSection).order_by(HomepageSection.position))
        ).all()

    async def list_public_navigation(self) -> Sequence[NavigationItem]:
        return (
            await self.session.scalars(
                select(NavigationItem)
                .where(
                    NavigationItem.status == PublicationStatus.PUBLISHED,
                    NavigationItem.is_visible.is_(True),
                    NavigationItem.archived_at.is_(None),
                )
                .order_by(NavigationItem.location, NavigationItem.sort_order)
            )
        ).all()

    async def list_active_features(self) -> Sequence[FeatureSetting]:
        return (
            await self.session.scalars(
                select(FeatureSetting)
                .where(FeatureSetting.archived_at.is_(None))
                .order_by(FeatureSetting.key)
            )
        ).all()

    async def list_feature_settings(self) -> Sequence[FeatureSetting]:
        return (
            await self.session.scalars(select(FeatureSetting).order_by(FeatureSetting.key))
        ).all()
