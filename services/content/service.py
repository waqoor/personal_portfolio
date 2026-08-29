from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from html import unescape
from math import ceil
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from packages.python.clients.storage import StorageClient
from packages.python.common.errors import ConflictError, NotFoundError, ValidationError
from packages.python.common.models import Base, PublicationStatus
from packages.python.common.policies import PublicationPolicy
from packages.python.common.repository import TransactionManager
from packages.python.common.schemas import Page
from packages.python.common.settings import Settings
from packages.python.common.uploads import validate_declared_metadata, validate_generic_media
from packages.python.contracts.features import FeatureResolution, FeatureState
from services.content.models import (
    Article,
    FeatureSetting,
    HomepageSection,
    HomepageSectionType,
    MediaAsset,
    NavigationItem,
)
from services.content.registry import HomepageSectionRegistry
from services.content.repository import ContentRepository
from services.content.schemas import (
    ArticleCreate,
    ArticlePage,
    ArticleRead,
    ArticleUpdate,
    FeatureSettingRead,
    FeatureSettingUpsert,
    HomepageCompositionUpdate,
    HomepageRead,
    HomepageSectionCreate,
    HomepageSectionPayload,
    HomepageSectionRead,
    HomepageSectionUpdate,
    MediaRead,
    MediaUpdate,
    MediaUploadMetadata,
    NavigationItemCreate,
    NavigationItemRead,
    NavigationItemUpdate,
    PublicArticleRead,
    PublicArticleSummaryRead,
    PublicSiteShellRead,
    SitePresentationSettings,
)
from services.identity.contracts import IdentityPublicReader
from services.portfolio.contracts import PortfolioPublicReader

ContentModel = TypeVar("ContentModel", bound=Base)
SchemaModel = TypeVar("SchemaModel", bound=BaseModel)
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
_MARKDOWN_LINK = re.compile(r"!?\[([^]]*)]\([^)]+\)")
_MARKDOWN_HTML = re.compile(r"<[^>]+>")
_MARKDOWN_MARKER = re.compile(r"(?:^|\s)[#>*_~`|+-]+(?=\s|$)", re.MULTILINE)
_READING_WORD = re.compile(r"[\w+#.-]+", re.UNICODE)


def _safe_filename(value: str, fallback: str) -> str:
    name = Path(value).name.strip().replace("\x00", "")
    return (_SAFE_FILENAME.sub("-", name).strip(".-") or fallback)[:255]


def _reading_minutes(markdown: str) -> int:
    """Estimate reading time from normalized rendered text at 200 words/minute."""

    text = _MARKDOWN_LINK.sub(r"\1", markdown)
    text = _MARKDOWN_HTML.sub(" ", text)
    text = _MARKDOWN_MARKER.sub(" ", text)
    words = _READING_WORD.findall(unescape(text))
    return max(1, ceil(len(words) / 200))


class ContentService:
    def __init__(
        self,
        repository: ContentRepository,
        transaction: TransactionManager,
        storage: StorageClient,
        settings: Settings,
        registry: HomepageSectionRegistry,
    ) -> None:
        self.repository = repository
        self.transaction = transaction
        self.storage = storage
        self.settings = settings
        self.registry = registry

    async def upload_media(
        self,
        metadata: MediaUploadMetadata,
        *,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> MediaRead:
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
        asset_id = uuid.uuid4()
        storage_key = f"media/{asset_id}{upload.extension}"
        stored = await self.storage.save(storage_key, upload.content)
        asset = MediaAsset(
            id=asset_id,
            storage_key=stored.key,
            original_filename=_safe_filename(filename, f"media{upload.extension}"),
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
        )
        PublicationPolicy.apply(asset, PublicationStatus.DRAFT)
        self.repository.add(asset)
        try:
            await self._commit_conflict("The media asset could not be stored due to a conflict.")
        except Exception:
            await self.storage.delete(storage_key)
            raise
        return MediaRead.model_validate(asset)

    async def get_media(self, media_id: UUID) -> MediaRead:
        return MediaRead.model_validate(await self._require(MediaAsset, media_id, "Media asset"))

    async def update_media(self, media_id: UUID, data: MediaUpdate) -> MediaRead:
        media = await self._require(MediaAsset, media_id, "Media asset")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(media, key, value)
        self._validate_media_accessibility(
            media.media_type, media.alt_text, media.caption, media.is_decorative
        )
        await self.transaction.commit()
        return MediaRead.model_validate(media)

    async def read_public_media(self, media_id: UUID) -> tuple[MediaRead, bytes]:
        media_read, storage_key = await self.get_public_media_file(media_id)
        return media_read, await self.storage.read(storage_key)

    async def get_public_media_file(self, media_id: UUID) -> tuple[MediaRead, str]:
        media = await self._require(MediaAsset, media_id, "Media asset")
        if not PublicationPolicy.is_public(media):
            raise NotFoundError("Media asset not found.")
        return MediaRead.model_validate(media), media.storage_key

    async def create_article(self, data: ArticleCreate) -> ArticleRead:
        hero_media = None
        if data.hero_media_id:
            hero_media = await self._require(MediaAsset, data.hero_media_id, "Hero media")
            self._validate_article_hero(hero_media)
        payload = data.model_dump()
        status = PublicationStatus(payload.pop("status"))
        if payload.get("reading_minutes") is None:
            payload["reading_minutes"] = _reading_minutes(payload["body_markdown"])
        article = Article(**payload)
        article.hero_media = hero_media
        PublicationPolicy.apply(article, status)
        self.repository.add(article)
        await self._commit_conflict("An article with this slug already exists.")
        return self._article_read(article, public=False)

    async def update_article(self, article_id: UUID, data: ArticleUpdate) -> ArticleRead:
        article = await self._require(Article, article_id, "Article")
        payload = data.model_dump(exclude_unset=True)
        if "body_markdown" in payload and "reading_minutes" not in payload:
            payload["reading_minutes"] = _reading_minutes(payload["body_markdown"])
        elif payload.get("reading_minutes") is None and "reading_minutes" in payload:
            payload["reading_minutes"] = _reading_minutes(
                payload.get("body_markdown", article.body_markdown)
            )
        if "hero_media_id" in payload:
            hero_media_id = payload.pop("hero_media_id")
            if hero_media_id:
                hero_media = await self._require(MediaAsset, hero_media_id, "Hero media")
                self._validate_article_hero(hero_media)
                article.hero_media = hero_media
            else:
                article.hero_media = None
        for key, value in payload.items():
            setattr(article, key, value)
        await self._commit_conflict("An article with this slug already exists.")
        return self._article_read(article, public=False)

    @staticmethod
    def _validate_article_hero(media: MediaAsset) -> None:
        if media.archived_at is not None:
            raise ValidationError("hero_media_id references an archived media asset.")
        if not media.media_type.startswith("image/"):
            raise ValidationError("Article hero media must be an image.")

    @staticmethod
    def _validate_media_accessibility(
        media_type: str, alt_text: str, caption: str | None, is_decorative: bool
    ) -> None:
        alt = alt_text.strip()
        if is_decorative:
            if not media_type.startswith("image/"):
                raise ValidationError("Only images can be decorative.")
            if alt:
                raise ValidationError("Decorative images must use empty alternative text.")
            return
        if media_type.startswith("image/") and not alt:
            raise ValidationError("Informative images require meaningful alternative text.")
        if not media_type.startswith("image/") and not (alt or (caption and caption.strip())):
            raise ValidationError("Documents and videos require an accessible label or caption.")

    async def create_section(self, data: HomepageSectionCreate) -> HomepageSectionRead:
        variant = data.variant or self.registry.default_variant(data.section_type)
        self.registry.validate(data.section_type, variant)
        payload = data.model_dump()
        payload["variant"] = variant
        payload["feature_key"] = data.feature_key or self.registry.feature_key(data.section_type)
        status = PublicationStatus(payload.pop("status"))
        section = HomepageSection(**payload)
        PublicationPolicy.apply(section, status)
        self.repository.add(section)
        await self._commit_conflict("Homepage section position already exists.")
        return self._section_read(section)

    async def update_section(
        self, section_id: UUID, data: HomepageSectionUpdate
    ) -> HomepageSectionRead:
        section = await self._require(HomepageSection, section_id, "Homepage section")
        payload = data.model_dump(exclude_unset=True)
        section_type = payload.get("section_type", section.section_type)
        if payload.get("feature_key", section.feature_key) is None:
            payload["feature_key"] = self.registry.feature_key(section_type)
        variant = payload.get("variant")
        if variant is None:
            variant = (
                self.registry.default_variant(section_type)
                if "section_type" in payload
                else self.registry.canonical_persisted_variant(section_type, section.variant)
            )
            if variant != section.variant or "variant" in payload or "section_type" in payload:
                payload["variant"] = variant
        self.registry.validate(section_type, variant)
        for key, value in payload.items():
            setattr(section, key, value)
        await self._commit_conflict("Homepage section position already exists.")
        return self._section_read(section)

    async def replace_homepage_composition(
        self, data: HomepageCompositionUpdate
    ) -> list[HomepageSectionRead]:
        """Replace the public composition atomically while retaining archived history."""

        existing = list(await self.repository.list_all_sections())
        existing_by_id = {section.id: section for section in existing}
        requested_ids: set[UUID] = set()
        requested_types: set[HomepageSectionType] = set()
        canonical_variants: list[str] = []

        for item in data.sections:
            variant = item.variant or self.registry.default_variant(item.section_type)
            if item.section_type in requested_types:
                raise ConflictError("Each homepage section type can appear only once.")
            requested_types.add(item.section_type)
            if item.id is None:
                self.registry.validate(item.section_type, variant)
                canonical_variants.append(variant)
                continue
            if item.id in requested_ids:
                raise ConflictError("A homepage section cannot appear more than once.")
            if item.id not in existing_by_id:
                raise NotFoundError("Homepage section not found.")
            persisted = existing_by_id[item.id]
            try:
                self.registry.validate(item.section_type, variant)
            except ValidationError:
                if persisted.section_type != item.section_type or persisted.variant != variant:
                    raise
                variant = self.registry.canonical_persisted_variant(item.section_type, variant)
            canonical_variants.append(variant)
            requested_ids.add(item.id)

        staging_base = max((section.position for section in existing), default=10_000)
        staging_base += len(existing) + 1
        for index, section in enumerate(existing):
            section.position = staging_base + index

        try:
            await self.repository.flush()

            selected: list[HomepageSection] = []
            for position, item in enumerate(data.sections):
                payload = item.model_dump(exclude={"id", "status"})
                payload["variant"] = canonical_variants[position]
                payload["feature_key"] = item.feature_key or self.registry.feature_key(
                    item.section_type
                )
                payload["position"] = position
                if item.id is None:
                    section = HomepageSection(**payload)
                    self.repository.add(section)
                else:
                    section = existing_by_id[item.id]
                    for key, value in payload.items():
                        setattr(section, key, value)
                PublicationPolicy.apply(section, PublicationStatus.PUBLISHED)
                selected.append(section)

            retained = [section for section in existing if section.id not in requested_ids]
            for offset, section in enumerate(retained, start=len(selected)):
                section.position = offset
                section.enabled = False
                PublicationPolicy.apply(section, PublicationStatus.ARCHIVED)

            await self.transaction.commit()
        except IntegrityError as exc:
            await self.transaction.rollback()
            raise ConflictError("The homepage composition contains conflicting entries.") from exc

        return [self._section_read(section) for section in selected]

    async def create_navigation(self, data: NavigationItemCreate) -> NavigationItemRead:
        payload = data.model_dump()
        status = PublicationStatus(payload.pop("status"))
        item = NavigationItem(**payload)
        PublicationPolicy.apply(item, status)
        self.repository.add(item)
        await self.transaction.commit()
        return NavigationItemRead.model_validate(item)

    async def update_navigation(
        self, item_id: UUID, data: NavigationItemUpdate
    ) -> NavigationItemRead:
        item = await self._require(NavigationItem, item_id, "Navigation item")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await self.transaction.commit()
        return NavigationItemRead.model_validate(item)

    async def upsert_feature(self, data: FeatureSettingUpsert) -> FeatureSettingRead:
        feature = await self.repository.get_feature_by_key(data.key)
        payload = data.model_dump()
        if feature is None:
            feature = FeatureSetting(**payload)
            self.repository.add(feature)
        else:
            for key, value in payload.items():
                setattr(feature, key, value)
            feature.archived_at = None
        await self._commit_conflict("A feature with this key already exists.")
        return FeatureSettingRead.model_validate(feature)

    async def archive_feature(self, feature_id: UUID) -> FeatureSettingRead:
        feature = await self._require(FeatureSetting, feature_id, "Feature setting")
        feature.enabled = False
        feature.archived_at = datetime.now(UTC)
        await self.transaction.commit()
        return FeatureSettingRead.model_validate(feature)

    async def set_status(
        self, resource: str, entity_id: UUID, status: PublicationStatus
    ) -> BaseModel:
        mapping: dict[str, tuple[type[Base], type[BaseModel]]] = {
            "media": (MediaAsset, MediaRead),
            "articles": (Article, ArticleRead),
            "sections": (HomepageSection, HomepageSectionRead),
            "navigation": (NavigationItem, NavigationItemRead),
        }
        selected = mapping.get(resource)
        if selected is None:
            raise NotFoundError("Unknown content resource.")
        model, schema = selected
        entity = await self._require(model, entity_id, resource.rstrip("s").title())
        if (
            status is PublicationStatus.PUBLISHED
            and isinstance(entity, MediaAsset)
            and not await self.storage.exists(entity.storage_key)
        ):
            raise ConflictError("The media file is missing from managed storage.")
        PublicationPolicy.apply(entity, status)  # type: ignore[arg-type]
        await self.transaction.commit()
        return schema.model_validate(entity)

    async def list_admin(
        self,
        resource: str,
        limit: int,
        offset: int,
        *,
        search: str | None = None,
        status: PublicationStatus | None = None,
    ) -> Page[Any]:
        mapping: dict[str, tuple[type[Base], type[BaseModel]]] = {
            "media": (MediaAsset, MediaRead),
            "articles": (Article, ArticleRead),
            "sections": (HomepageSection, HomepageSectionRead),
            "navigation": (NavigationItem, NavigationItemRead),
            "features": (FeatureSetting, FeatureSettingRead),
        }
        selected = mapping.get(resource)
        if selected is None:
            raise NotFoundError("Unknown content resource.")
        model, schema = selected
        entities, total = await self.repository.list_entities(
            model,
            limit=limit,
            offset=offset,
            search=search,
            status=status,
        )
        return Page(
            items=[
                self._section_read(entity)
                if isinstance(entity, HomepageSection)
                else schema.model_validate(entity)
                for entity in entities
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_public_article(self, slug: str) -> PublicArticleRead:
        article = await self.repository.get_public_article_by_slug(slug)
        if article is None:
            raise NotFoundError("Article not found.")
        related = await self.repository.list_related_public_articles(article, limit=3)
        return self._public_article(article).model_copy(
            update={"related_articles": [self._public_article_summary(item) for item in related]}
        )

    async def list_public_articles(self, limit: int = 20) -> list[PublicArticleSummaryRead]:
        articles, _ = await self.repository.list_entities(Article, limit=limit, public=True)
        return [self._public_article_summary(article) for article in articles]

    async def search_public_articles(self, query: str, *, limit: int) -> list[PublicArticleRead]:
        articles = await self.repository.search_public_articles(query, limit=limit)
        return [self._public_article(article) for article in articles]

    async def list_public_articles_page(
        self,
        *,
        limit: int,
        offset: int,
        topic: str | None = None,
        search: str | None = None,
    ) -> ArticlePage:
        articles, total = await self.repository.list_public_articles_page(
            limit=limit,
            offset=offset,
            topic=topic,
            search=search,
        )
        return ArticlePage(
            items=[self._public_article_summary(article) for article in articles],
            total=total,
            limit=limit,
            offset=offset,
            topics=await self.repository.list_public_article_topics(),
        )

    async def list_public_sections(self) -> list[HomepageSectionRead]:
        return [
            self._section_read(section) for section in await self.repository.list_public_sections()
        ]

    async def list_public_navigation(self) -> list[NavigationItemRead]:
        return [
            NavigationItemRead.model_validate(item)
            for item in await self.repository.list_public_navigation()
        ]

    async def active_feature_map(self) -> dict[str, bool]:
        return {
            key: resolution.enabled for key, resolution in (await self.feature_state_map()).items()
        }

    async def feature_state_map(self) -> dict[str, FeatureResolution]:
        return {
            feature.key: self._resolve_feature_row(feature, default=False)
            for feature in await self.repository.list_feature_settings()
        }

    async def resolve_feature(self, key: str, *, default: bool) -> FeatureResolution:
        feature = await self.repository.get_feature_by_key(key)
        return self._resolve_feature_row(feature, default=default)

    @staticmethod
    def _resolve_feature_row(feature: FeatureSetting | None, *, default: bool) -> FeatureResolution:
        if feature is None:
            return FeatureResolution(FeatureState.UNCONFIGURED, default)
        if feature.archived_at is not None:
            return FeatureResolution(FeatureState.ARCHIVED, False)
        if feature.enabled:
            return FeatureResolution(FeatureState.ENABLED, True)
        return FeatureResolution(FeatureState.DISABLED, False)

    async def active_feature_configurations(self) -> dict[str, dict[str, Any]]:
        return {
            feature.key: dict(feature.configuration)
            for feature in await self.repository.list_active_features()
        }

    async def active_feature_configuration(self, key: str) -> dict[str, Any]:
        feature = await self.repository.get_feature_by_key(key)
        if feature is None or feature.archived_at is not None:
            return {}
        return dict(feature.configuration)

    async def get_site_presentation(self) -> SitePresentationSettings:
        return SitePresentationSettings.from_persisted_configuration(
            await self.active_feature_configuration("site_settings")
        )

    def _section_read(self, section: HomepageSection) -> HomepageSectionRead:
        variant = self.registry.canonical_persisted_variant(section.section_type, section.variant)
        return HomepageSectionRead.model_validate(section).model_copy(update={"variant": variant})

    @staticmethod
    def _article_read(article: Article, *, public: bool) -> ArticleRead:
        response = ArticleRead.model_validate(article)
        if public and article.hero_media and not PublicationPolicy.is_public(article.hero_media):
            response.hero_media = None
        return response

    @staticmethod
    def _public_article_summary(article: Article) -> PublicArticleSummaryRead:
        response = PublicArticleSummaryRead.model_validate(article)
        if article.hero_media and not PublicationPolicy.is_public(article.hero_media):
            response.hero_media = None
        return response

    @staticmethod
    def _public_article(article: Article) -> PublicArticleRead:
        response = PublicArticleRead.model_validate(article)
        if article.hero_media and not PublicationPolicy.is_public(article.hero_media):
            response.hero_media = None
        return response

    async def _require(
        self, model: type[ContentModel], entity_id: UUID, label: str
    ) -> ContentModel:
        entity = await self.repository.get(model, entity_id)
        if entity is None:
            raise NotFoundError(f"{label} not found.")
        return entity

    async def _commit_conflict(self, message: str) -> None:
        try:
            await self.transaction.commit()
        except IntegrityError as exc:
            await self.transaction.rollback()
            raise ConflictError(message) from exc


class HomepageComposer:
    """Content-owned composition using public contracts from peer services."""

    def __init__(
        self,
        content: ContentService,
        identity: IdentityPublicReader,
        portfolio: PortfolioPublicReader,
        registry: HomepageSectionRegistry,
        runtime_feature_caps: Mapping[str, bool] | None = None,
        assistant_max_question_length: int | None = None,
    ) -> None:
        self.content = content
        self.identity = identity
        self.portfolio = portfolio
        self.registry = registry
        self.runtime_feature_caps = dict(runtime_feature_caps or {})
        self.assistant_max_question_length = assistant_max_question_length

    async def compose(self) -> HomepageRead:
        profile = await self.identity.get_public_profile()
        resume = await self.identity.get_public_current_resume()
        navigation = await self.content.list_public_navigation()
        features = await self.content.active_feature_map()
        feature_configurations = await self.content.active_feature_configurations()
        if self.assistant_max_question_length is not None:
            assistant_configuration = feature_configurations.setdefault("assistant", {})
            configured_limit = assistant_configuration.get("max_question_length")
            assistant_configuration["max_question_length"] = min(
                configured_limit
                if type(configured_limit) is int and configured_limit >= 50
                else self.assistant_max_question_length,
                self.assistant_max_question_length,
            )
        for key, available in self.runtime_feature_caps.items():
            resolution = await self.content.resolve_feature(key, default=True)
            features[key] = available and resolution.enabled
        sections = await self.content.list_public_sections()
        payloads: list[HomepageSectionPayload] = []
        for section in sections:
            feature_key = section.feature_key or self.registry.feature_key(section.section_type)
            if feature_key and not features.get(feature_key, False):
                continue
            limit = section.data_limit or self.registry.default_limit(section.section_type) or 20
            data = await self._resolve(section.section_type, limit, profile, resume, section)
            payloads.append(HomepageSectionPayload(section=section, data=data))
        return HomepageRead(
            profile=profile,
            current_resume=resume,
            navigation=navigation,
            features=features,
            feature_configurations=feature_configurations,
            site_presentation=SitePresentationSettings.from_persisted_configuration(
                feature_configurations.get("site_settings", {})
            ),
            sections=payloads,
        )

    async def compose_site_shell(self) -> PublicSiteShellRead:
        profile = await self.identity.get_public_profile()
        navigation = await self.content.list_public_navigation()
        features = await self.content.active_feature_map()
        configurations = await self.content.active_feature_configurations()
        for key, available in self.runtime_feature_caps.items():
            resolution = await self.content.resolve_feature(key, default=True)
            features[key] = available and resolution.enabled
        if self.assistant_max_question_length is not None:
            assistant = configurations.setdefault("assistant", {})
            configured = assistant.get("max_question_length")
            assistant["max_question_length"] = min(
                configured
                if type(configured) is int and configured >= 50
                else self.assistant_max_question_length,
                self.assistant_max_question_length,
            )
        return PublicSiteShellRead(
            profile=profile,
            navigation=navigation,
            features=features,
            feature_configurations=configurations,
            site_presentation=SitePresentationSettings.from_persisted_configuration(
                configurations.get("site_settings", {})
            ),
        )

    async def _resolve(
        self,
        section_type: HomepageSectionType,
        limit: int,
        profile: Any,
        resume: Any,
        section: HomepageSectionRead,
    ) -> Any:
        if section_type is HomepageSectionType.HERO:
            return profile
        if section_type is HomepageSectionType.RESUME:
            return resume
        if section_type is HomepageSectionType.AVAILABILITY:
            if profile is None:
                return None
            return {
                "status": profile.availability_status,
                "detail": profile.availability_detail,
            }
        if section_type in {HomepageSectionType.WHAT_I_BUILD, HomepageSectionType.CATEGORIES}:
            return await self.portfolio.list_public_categories(limit)
        if section_type is HomepageSectionType.SELECTED_WORK:
            return await self.portfolio.list_public_projects(limit, featured_only=True)
        if section_type is HomepageSectionType.METRICS:
            return await self.portfolio.list_public_metrics(limit)
        if section_type is HomepageSectionType.TESTIMONIALS:
            return await self.portfolio.list_public_testimonials(limit)
        if section_type is HomepageSectionType.SECTORS:
            return await self.portfolio.list_public_sectors(limit)
        if section_type is HomepageSectionType.SKILLS:
            return await self.portfolio.list_public_skills(limit)
        if section_type is HomepageSectionType.EXPERIENCE:
            return await self.portfolio.list_public_experiences(limit)
        if section_type is HomepageSectionType.EDUCATION:
            return await self.portfolio.list_public_education(limit)
        if section_type is HomepageSectionType.CERTIFICATIONS:
            return await self.portfolio.list_public_certifications(limit)
        if section_type is HomepageSectionType.OPEN_SOURCE:
            projects = await self.portfolio.list_public_projects(limit)
            return [project for project in projects if project.is_open_source]
        if section_type is HomepageSectionType.WRITING:
            return await self.content.list_public_articles(limit)
        if section_type is HomepageSectionType.SOCIAL_LINKS:
            return profile.social_links[:limit] if profile else []
        return section.configuration
