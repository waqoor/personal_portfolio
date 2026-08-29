from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

from pydantic import Field
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
    validate_image,
    validate_pdf,
)
from packages.python.contracts.seeding import SeedKey, SeedRecord, SeedSource, SeedStats
from services.identity.models import PortraitAsset, Profile, ResumeVersion, SocialLink
from services.identity.repository import IdentityRepository
from services.identity.schemas import ProfileCreate, SocialLinkBase


class SeedSocialLink(APIModel):
    seed_key: SeedKey
    profile_seed_key: SeedKey
    payload: SocialLinkBase


class SeedResumeVersion(APIModel):
    seed_key: SeedKey
    profile_seed_key: SeedKey
    file: str = Field(min_length=1, max_length=500)
    version_label: str = Field(min_length=1, max_length=120)
    effective_date: date | None = None
    download_name: str = Field(default="resume.pdf", min_length=1, max_length=255)
    status: PublicationStatus = PublicationStatus.DRAFT
    make_current: bool = False


class SeedPortrait(APIModel):
    seed_key: SeedKey
    profile_seed_key: SeedKey
    file: str = Field(min_length=1, max_length=500)
    media_type: str = Field(pattern=r"^image/(jpeg|png|webp|avif)$")
    alt_text: str = Field(min_length=1, max_length=300)
    width: int | None = Field(default=None, ge=1, le=50_000)
    height: int | None = Field(default=None, ge=1, le=50_000)
    sort_order: int = Field(default=0, ge=0, le=10_000)
    make_primary: bool = False


class IdentitySeedData(APIModel):
    profiles: list[SeedRecord[ProfileCreate]] = Field(default_factory=list)
    social_links: list[SeedSocialLink] = Field(default_factory=list)
    portraits: list[SeedPortrait] = Field(default_factory=list)
    resume_versions: list[SeedResumeVersion] = Field(default_factory=list)


class IdentitySeeder:
    def __init__(
        self,
        repository: IdentityRepository,
        transaction: TransactionManager,
        storage: StorageClient,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.transaction = transaction
        self.storage = storage
        self.settings = settings

    async def apply(
        self,
        data: IdentitySeedData,
        *,
        source: SeedSource,
        base_directory: Path,
    ) -> SeedStats:
        stats = SeedStats()
        for profile_record in data.profiles:
            if await self.repository.get_profile_by_seed_key(profile_record.seed_key):
                stats.add_skipped()
                continue
            payload = profile_record.payload.model_dump()
            for key, value in list(payload.items()):
                if value is not None and key.endswith("_url"):
                    payload[key] = str(value)
            status = PublicationStatus(payload.pop("status"))
            requested_primary = bool(payload.pop("is_primary"))
            profile = Profile(
                **payload,
                seed_key=profile_record.seed_key,
                seed_source=source.value,
                seeded_at=datetime.now(UTC),
                is_primary=requested_primary and not await self.repository.has_primary_profile(),
            )
            PublicationPolicy.apply(profile, status)
            self.repository.add_profile(profile)
            stats.add_created()
        await self.repository.session.flush()

        profiles = {
            profile_record.seed_key: await self.repository.get_profile_by_seed_key(
                profile_record.seed_key
            )
            for profile_record in data.profiles
        }
        for social_record in data.social_links:
            if await self.repository.get_social_link_by_seed_key(social_record.seed_key):
                stats.add_skipped()
                continue
            social_profile = profiles.get(social_record.profile_seed_key) or (
                await self.repository.get_profile_by_seed_key(social_record.profile_seed_key)
            )
            if social_profile is None:
                raise ValidationError(
                    f"Unknown profile seed key '{social_record.profile_seed_key}'."
                )
            existing_link = cast(
                SocialLink | None,
                await self.repository.session.scalar(
                    select(SocialLink).where(
                        SocialLink.profile_id == social_profile.id,
                        SocialLink.url == str(social_record.payload.url),
                    )
                ),
            )
            if existing_link:
                stats.add_skipped()
                continue
            link = SocialLink(
                **social_record.payload.model_dump(mode="json"),
                profile_id=social_profile.id,
                seed_key=social_record.seed_key,
                seed_source=source.value,
                seeded_at=datetime.now(UTC),
            )
            self.repository.add_social_link(link)
            stats.add_created()
        await self.repository.session.flush()

        for portrait_record in data.portraits:
            if await self.repository.get_portrait_by_seed_key(portrait_record.seed_key):
                stats.add_skipped()
                continue
            portrait_profile = await self.repository.get_profile_by_seed_key(
                portrait_record.profile_seed_key
            )
            if portrait_profile is None:
                raise ValidationError(
                    f"Unknown profile seed key '{portrait_record.profile_seed_key}'."
                )
            content = self._read_contained_file(base_directory, portrait_record.file)
            upload = validate_image(
                content, portrait_record.media_type, self.settings.max_portrait_bytes
            )
            validate_declared_metadata(
                upload,
                width=portrait_record.width,
                height=portrait_record.height,
                duration_seconds=None,
            )
            storage_key = f"seed/portraits/{portrait_record.seed_key}{upload.extension}"
            stored = await self.storage.save(storage_key, upload.content)
            make_primary = (
                portrait_record.make_primary
                and not await self.repository.has_primary_portrait(portrait_profile.id)
            )
            portrait = PortraitAsset(
                profile_id=portrait_profile.id,
                storage_key=stored.key,
                original_filename=Path(portrait_record.file).name[:255],
                media_type=upload.media_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                alt_text=portrait_record.alt_text,
                width=upload.width,
                height=upload.height,
                sort_order=portrait_record.sort_order,
                is_primary=make_primary,
                seed_key=portrait_record.seed_key,
                seed_source=source.value,
                seeded_at=datetime.now(UTC),
            )
            self.repository.add_portrait(portrait)
            stats.add_created()
        await self.repository.session.flush()

        for resume_record in data.resume_versions:
            if await self.repository.get_resume_by_seed_key(resume_record.seed_key):
                stats.add_skipped()
                continue
            resume_profile = await self.repository.get_profile_by_seed_key(
                resume_record.profile_seed_key
            )
            if resume_profile is None:
                raise ValidationError(
                    f"Unknown profile seed key '{resume_record.profile_seed_key}'."
                )
            content = self._read_contained_file(base_directory, resume_record.file)
            upload = validate_pdf(content, "application/pdf", self.settings.max_resume_bytes)
            storage_key = f"seed/resumes/{resume_record.seed_key}.pdf"
            stored = await self.storage.save(storage_key, upload.content)
            resume = ResumeVersion(
                profile_id=resume_profile.id,
                version_label=resume_record.version_label,
                storage_key=stored.key,
                original_filename=safe_filename(Path(resume_record.file).name, "resume.pdf"),
                media_type=upload.media_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                effective_date=resume_record.effective_date,
                download_name=safe_filename(resume_record.download_name, "resume.pdf"),
                is_current=False,
                seed_key=resume_record.seed_key,
                seed_source=source.value,
                seeded_at=datetime.now(UTC),
            )
            PublicationPolicy.apply(resume, resume_record.status)
            if resume_record.make_current and resume_record.status is PublicationStatus.PUBLISHED:
                current = await self.repository.get_any_current_resume()
                if current is None:
                    resume.is_current = True
            self.repository.add_resume(resume)
            stats.add_created()
        await self.repository.session.flush()
        return stats

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
