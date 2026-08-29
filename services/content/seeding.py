from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from pydantic import Field, model_validator
from sqlalchemy import select

from packages.python.clients.storage import StorageClient
from packages.python.common.errors import ValidationError
from packages.python.common.models import PublicationStatus
from packages.python.common.policies import PublicationPolicy
from packages.python.common.repository import TransactionManager
from packages.python.common.schemas import APIModel
from packages.python.common.settings import Settings
from packages.python.common.uploads import (
    safe_filename,
    validate_declared_metadata,
    validate_generic_media,
)
from packages.python.contracts.seeding import SeedKey, SeedRecord, SeedSource, SeedStats
from services.content.models import (
    Article,
    FeatureSetting,
    HomepageSection,
    MediaAsset,
    NavigationItem,
)
from services.content.registry import HomepageSectionRegistry
from services.content.repository import ContentRepository
from services.content.schemas import (
    ArticleCreate,
    FeatureSettingUpsert,
    HomepageSectionCreate,
    MediaUploadMetadata,
    NavigationItemCreate,
)


class SeedMedia(APIModel):
    seed_key: SeedKey
    file: str = Field(min_length=1, max_length=500)
    media_type: str = Field(min_length=1, max_length=100)
    metadata: MediaUploadMetadata
    status: PublicationStatus = PublicationStatus.DRAFT


class SeedArticle(APIModel):
    seed_key: SeedKey
    hero_media_seed_key: SeedKey | None = None
    payload: ArticleCreate

    @model_validator(mode="after")
    def forbid_uuid_reference(self) -> SeedArticle:
        if self.payload.hero_media_id is not None:
            raise ValueError("seed articles must reference hero media by seed key")
        return self


class ContentSeedData(APIModel):
    media: list[SeedMedia] = Field(default_factory=list)
    articles: list[SeedArticle] = Field(default_factory=list)
    homepage_sections: list[SeedRecord[HomepageSectionCreate]] = Field(default_factory=list)
    navigation: list[SeedRecord[NavigationItemCreate]] = Field(default_factory=list)
    features: list[SeedRecord[FeatureSettingUpsert]] = Field(default_factory=list)


class ContentSeeder:
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

    async def apply(
        self,
        data: ContentSeedData,
        *,
        source: SeedSource,
        base_directory: Path,
    ) -> SeedStats:
        stats = SeedStats()
        media_by_seed: dict[str, MediaAsset] = {}
        for media_record in data.media:
            existing_media = await self.repository.get_by_seed_key(
                MediaAsset, media_record.seed_key
            )
            if existing_media:
                media_by_seed[media_record.seed_key] = existing_media
                stats.add_skipped()
                continue
            content = self._read_contained_file(base_directory, media_record.file)
            upload = validate_generic_media(
                content, media_record.media_type, self.settings.max_media_bytes
            )
            validate_declared_metadata(
                upload,
                width=media_record.metadata.width,
                height=media_record.metadata.height,
                duration_seconds=media_record.metadata.duration_seconds,
            )
            storage_key = f"seed/media/{media_record.seed_key}{upload.extension}"
            stored = await self.storage.save(storage_key, upload.content)
            asset = MediaAsset(
                storage_key=stored.key,
                original_filename=safe_filename(Path(media_record.file).name, "media"),
                media_type=upload.media_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                **media_record.metadata.model_dump(exclude={"width", "height", "duration_seconds"}),
                width=upload.width,
                height=upload.height,
                duration_seconds=upload.duration_seconds,
                **self._provenance(media_record.seed_key, source),
            )
            PublicationPolicy.apply(asset, media_record.status)
            self.repository.add(asset)
            media_by_seed[media_record.seed_key] = asset
            stats.add_created()
        await self.repository.session.flush()

        for article_record in data.articles:
            existing_article = await self.repository.get_by_seed_key(
                Article, article_record.seed_key
            )
            if existing_article is None:
                existing_article = cast(
                    Article | None,
                    await self.repository.session.scalar(
                        select(Article).where(Article.slug == article_record.payload.slug)
                    ),
                )
            if existing_article:
                stats.add_skipped()
                continue
            payload = article_record.payload.model_dump()
            status = PublicationStatus(payload.pop("status"))
            payload.pop("hero_media_id", None)
            hero = await self._media_reference(article_record.hero_media_seed_key, media_by_seed)
            article = Article(
                **payload,
                hero_media_id=hero.id if hero else None,
                **self._provenance(article_record.seed_key, source),
            )
            PublicationPolicy.apply(article, status)
            self.repository.add(article)
            stats.add_created()

        for section_record in data.homepage_sections:
            existing_section = await self.repository.get_by_seed_key(
                HomepageSection, section_record.seed_key
            )
            if existing_section is None:
                existing_section = cast(
                    HomepageSection | None,
                    await self.repository.session.scalar(
                        select(HomepageSection).where(
                            HomepageSection.position == section_record.payload.position
                        )
                    ),
                )
            if existing_section:
                stats.add_skipped()
                continue
            variant = section_record.payload.variant or self.registry.default_variant(
                section_record.payload.section_type
            )
            self.registry.validate(section_record.payload.section_type, variant)
            payload = section_record.payload.model_dump()
            payload["variant"] = variant
            status = PublicationStatus(payload.pop("status"))
            section = HomepageSection(
                **payload, **self._provenance(section_record.seed_key, source)
            )
            PublicationPolicy.apply(section, status)
            self.repository.add(section)
            stats.add_created()

        for navigation_record in data.navigation:
            existing_navigation = await self.repository.get_by_seed_key(
                NavigationItem, navigation_record.seed_key
            )
            if existing_navigation is None:
                existing_navigation = cast(
                    NavigationItem | None,
                    await self.repository.session.scalar(
                        select(NavigationItem).where(
                            NavigationItem.href == navigation_record.payload.href,
                            NavigationItem.location == navigation_record.payload.location,
                        )
                    ),
                )
            if existing_navigation:
                stats.add_skipped()
                continue
            payload = navigation_record.payload.model_dump()
            status = PublicationStatus(payload.pop("status"))
            item = NavigationItem(**payload, **self._provenance(navigation_record.seed_key, source))
            PublicationPolicy.apply(item, status)
            self.repository.add(item)
            stats.add_created()

        for feature_record in data.features:
            existing_feature = await self.repository.get_by_seed_key(
                FeatureSetting, feature_record.seed_key
            )
            if existing_feature is None:
                existing_feature = await self.repository.get_feature_by_key(
                    feature_record.payload.key
                )
            if existing_feature:
                stats.add_skipped()
                continue
            feature = FeatureSetting(
                **feature_record.payload.model_dump(),
                **self._provenance(feature_record.seed_key, source),
            )
            self.repository.add(feature)
            stats.add_created()
        await self.repository.session.flush()
        return stats

    async def _media_reference(
        self, seed_key: str | None, local: dict[str, MediaAsset]
    ) -> MediaAsset | None:
        if seed_key is None:
            return None
        media = local.get(seed_key) or await self.repository.get_by_seed_key(MediaAsset, seed_key)
        if media is None:
            raise ValidationError(f"Unknown media seed key '{seed_key}'.")
        return media

    @staticmethod
    def _read_contained_file(base_directory: Path, value: str) -> bytes:
        base = base_directory.resolve()
        candidate = (base / value).resolve()
        if not candidate.is_relative_to(base) or not candidate.is_file():
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
            raise ValidationError(
                f"Seed asset is missing or outside the manifest directory ({digest})."
            )
        return candidate.read_bytes()

    @staticmethod
    def _provenance(seed_key: str, source: SeedSource) -> dict[str, object]:
        return {
            "seed_key": seed_key,
            "seed_source": source.value,
            "seeded_at": datetime.now(UTC),
        }
