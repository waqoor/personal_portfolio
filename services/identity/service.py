from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from packages.python.clients.storage import StorageClient
from packages.python.common.errors import ConflictError, NotFoundError
from packages.python.common.models import PublicationStatus
from packages.python.common.policies import PublicationPolicy
from packages.python.common.repository import TransactionManager
from packages.python.common.schemas import Page
from packages.python.common.settings import Settings
from packages.python.common.uploads import (
    safe_filename,
    validate_declared_metadata,
    validate_image,
    validate_pdf,
)
from services.identity.contracts import IdentityPublicReader
from services.identity.models import PortraitAsset, Profile, ResumeVersion, SocialLink
from services.identity.repository import IdentityRepository
from services.identity.schemas import (
    PortraitRead,
    PortraitUploadMetadata,
    ProfileCreate,
    ProfileRead,
    ProfileUpdate,
    PublicResumeRead,
    ResumeRead,
    ResumeUploadMetadata,
    SocialLinkCreate,
    SocialLinkRead,
    SocialLinkUpdate,
)


class IdentityService(IdentityPublicReader):
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

    async def create_profile(self, data: ProfileCreate) -> ProfileRead:
        payload = data.model_dump(mode="json")
        status = PublicationStatus(payload.pop("status"))
        make_primary = bool(payload.pop("is_primary"))
        profile = Profile(**payload, is_primary=make_primary)
        PublicationPolicy.apply(profile, status)
        if make_primary or await self.repository.profile_count() == 0:
            await self.repository.clear_primary_profiles()
            profile.is_primary = True
        self.repository.add_profile(profile)
        await self._commit_conflict("A profile with this seed identity already exists.")
        loaded = await self.repository.get_profile(profile.id)
        return ProfileRead.model_validate(loaded or profile)

    async def update_profile(self, profile_id: UUID, data: ProfileUpdate) -> ProfileRead:
        profile = await self._require_profile(profile_id)
        changes = data.model_dump(exclude_unset=True, mode="json")
        make_primary = changes.pop("is_primary", None)
        for key, value in changes.items():
            setattr(profile, key, value)
        self._validate_profile_ctas(profile)
        if make_primary is True:
            await self.repository.clear_primary_profiles(excluding=profile.id)
            profile.is_primary = True
        elif make_primary is False and profile.is_primary:
            raise ConflictError("A primary profile cannot be unset without selecting another one.")
        await self.transaction.commit()
        loaded = await self.repository.get_profile(profile.id)
        return ProfileRead.model_validate(loaded or profile)

    @staticmethod
    def _validate_profile_ctas(profile: Profile) -> None:
        for name, label, url in (
            ("primary", profile.primary_cta_label, profile.primary_cta_url),
            ("secondary", profile.secondary_cta_label, profile.secondary_cta_url),
        ):
            if bool(label and label.strip()) != bool(url):
                raise ConflictError(f"{name.title()} CTA label and URL must be provided together.")

    async def set_profile_status(self, profile_id: UUID, status: PublicationStatus) -> ProfileRead:
        profile = await self._require_profile(profile_id)
        PublicationPolicy.apply(profile, status)
        await self.transaction.commit()
        loaded = await self.repository.get_profile(profile.id)
        return ProfileRead.model_validate(loaded or profile)

    async def list_profiles(
        self,
        limit: int,
        offset: int,
        *,
        search: str | None = None,
        status: PublicationStatus | None = None,
    ) -> Page[ProfileRead]:
        profiles, total = await self.repository.list_profiles(
            limit=limit,
            offset=offset,
            search=search,
            status=status,
        )
        return Page(
            items=[ProfileRead.model_validate(profile) for profile in profiles],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_profile(self, profile_id: UUID) -> ProfileRead:
        return ProfileRead.model_validate(await self._require_profile(profile_id))

    async def get_public_profile(self) -> ProfileRead | None:
        profile = await self.repository.get_public_profile()
        if profile is None:
            return None
        response = ProfileRead.model_validate(profile)
        response.portraits = [portrait for portrait in response.portraits if portrait.is_active]
        response.social_links = [link for link in response.social_links if link.is_visible]
        response.portraits.sort(key=lambda item: (not item.is_primary, item.sort_order))
        response.social_links.sort(key=lambda item: item.sort_order)
        return response

    async def upload_portrait(
        self,
        metadata: PortraitUploadMetadata,
        *,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> PortraitRead:
        await self._require_profile(metadata.profile_id)
        upload = validate_image(content, content_type, self.settings.max_portrait_bytes)
        validate_declared_metadata(
            upload,
            width=metadata.width,
            height=metadata.height,
            duration_seconds=None,
        )
        asset_id = uuid.uuid4()
        storage_key = f"portraits/{metadata.profile_id}/{asset_id}{upload.extension}"
        stored = await self.storage.save(storage_key, upload.content)
        portrait = PortraitAsset(
            id=asset_id,
            profile_id=metadata.profile_id,
            storage_key=stored.key,
            original_filename=safe_filename(filename, f"portrait{upload.extension}"),
            media_type=upload.media_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            alt_text=metadata.alt_text,
            width=upload.width,
            height=upload.height,
            sort_order=metadata.sort_order,
            is_primary=metadata.make_primary,
        )
        if metadata.make_primary:
            await self.repository.clear_primary_portraits(metadata.profile_id)
        self.repository.add_portrait(portrait)
        try:
            await self._commit_conflict("The portrait could not be stored due to a conflict.")
        except Exception:
            await self.storage.delete(storage_key)
            raise
        return PortraitRead.model_validate(portrait)

    async def set_primary_portrait(self, portrait_id: UUID) -> PortraitRead:
        portrait = await self._require_portrait(portrait_id)
        if not portrait.is_active:
            raise ConflictError("An archived portrait cannot be selected as primary.")
        await self.repository.clear_primary_portraits(portrait.profile_id, excluding=portrait.id)
        portrait.is_primary = True
        await self.transaction.commit()
        return PortraitRead.model_validate(portrait)

    async def archive_portrait(self, portrait_id: UUID) -> PortraitRead:
        portrait = await self._require_portrait(portrait_id)
        portrait.is_active = False
        portrait.is_primary = False
        await self.transaction.commit()
        return PortraitRead.model_validate(portrait)

    async def read_public_portrait_file(self, portrait_id: UUID) -> tuple[PortraitRead, bytes]:
        portrait_read, storage_key = await self.get_public_portrait_file(portrait_id)
        return portrait_read, await self.storage.read(storage_key)

    async def get_public_portrait_file(self, portrait_id: UUID) -> tuple[PortraitRead, str]:
        portrait = await self._require_portrait(portrait_id)
        profile = await self.repository.get_profile(portrait.profile_id)
        if profile is None or not portrait.is_active or not PublicationPolicy.is_public(profile):
            raise NotFoundError("Portrait not found.")
        return PortraitRead.model_validate(portrait), portrait.storage_key

    async def upload_resume(
        self,
        metadata: ResumeUploadMetadata,
        *,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> ResumeRead:
        await self._require_profile(metadata.profile_id)
        upload = validate_pdf(content, content_type, self.settings.max_resume_bytes)
        asset_id = uuid.uuid4()
        storage_key = f"resumes/{metadata.profile_id}/{asset_id}.pdf"
        stored = await self.storage.save(storage_key, upload.content)
        resume = ResumeVersion(
            id=asset_id,
            profile_id=metadata.profile_id,
            version_label=metadata.version_label,
            storage_key=stored.key,
            original_filename=safe_filename(filename, "resume.pdf"),
            media_type=upload.media_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            effective_date=metadata.effective_date,
            download_name=safe_filename(metadata.download_name, "resume.pdf"),
            is_current=False,
        )
        PublicationPolicy.apply(resume, PublicationStatus.DRAFT)
        self.repository.add_resume(resume)
        try:
            await self._commit_conflict("The résumé version could not be stored due to a conflict.")
        except Exception:
            await self.storage.delete(storage_key)
            raise
        return ResumeRead.model_validate(resume)

    async def list_resume_versions(self, profile_id: UUID) -> list[ResumeRead]:
        await self._require_profile(profile_id)
        return [
            ResumeRead.model_validate(resume)
            for resume in await self.repository.list_resumes(profile_id)
        ]

    async def publish_and_set_current_resume(self, resume_id: UUID) -> ResumeRead:
        resume = await self._require_resume(resume_id)
        profile = await self._require_profile(resume.profile_id)
        if not PublicationPolicy.is_public(profile):
            raise ConflictError("Publish the owning profile before selecting its current résumé.")
        if not await self.storage.exists(resume.storage_key):
            raise ConflictError("The résumé file is missing from managed storage.")
        await self.repository.clear_current_resumes(excluding=resume.id)
        PublicationPolicy.apply(resume, PublicationStatus.PUBLISHED)
        resume.is_current = True
        await self.transaction.commit()
        return ResumeRead.model_validate(resume)

    async def archive_resume(self, resume_id: UUID) -> ResumeRead:
        resume = await self._require_resume(resume_id)
        if resume.is_current:
            raise ConflictError("Select another current résumé before archiving this version.")
        PublicationPolicy.apply(resume, PublicationStatus.ARCHIVED)
        await self.transaction.commit()
        return ResumeRead.model_validate(resume)

    async def get_public_current_resume(self) -> PublicResumeRead | None:
        profile = await self.repository.get_public_profile()
        if profile is None:
            return None
        resume = await self.repository.get_public_current_resume(profile.id)
        return PublicResumeRead.model_validate(resume) if resume else None

    async def read_public_resume_file(self) -> tuple[PublicResumeRead, bytes]:
        resume_read, storage_key = await self.get_public_resume_file()
        return resume_read, await self.storage.read(storage_key)

    async def get_public_resume_file(self) -> tuple[PublicResumeRead, str]:
        profile = await self.repository.get_public_profile()
        if profile is None:
            raise NotFoundError("No published résumé is currently available.")
        resume = await self.repository.get_public_current_resume(profile.id)
        if resume is None:
            raise NotFoundError("No published résumé is currently available.")
        return PublicResumeRead.model_validate(resume), resume.storage_key

    async def create_social_link(self, data: SocialLinkCreate) -> SocialLinkRead:
        await self._require_profile(data.profile_id)
        link = SocialLink(
            profile_id=data.profile_id,
            **data.model_dump(mode="json", exclude={"profile_id"}),
        )
        self.repository.add_social_link(link)
        await self.transaction.commit()
        return SocialLinkRead.model_validate(link)

    async def update_social_link(self, link_id: UUID, data: SocialLinkUpdate) -> SocialLinkRead:
        link = await self._require_social_link(link_id)
        for key, value in data.model_dump(exclude_unset=True, mode="json").items():
            setattr(link, key, value)
        await self.transaction.commit()
        return SocialLinkRead.model_validate(link)

    async def delete_social_link(self, link_id: UUID) -> None:
        link = await self._require_social_link(link_id)
        await self.repository.delete_social_link(link)
        await self.transaction.commit()

    async def _require_profile(self, profile_id: UUID) -> Profile:
        profile = await self.repository.get_profile(profile_id)
        if profile is None:
            raise NotFoundError("Profile not found.")
        return profile

    async def _require_portrait(self, portrait_id: UUID) -> PortraitAsset:
        portrait = await self.repository.get_portrait(portrait_id)
        if portrait is None:
            raise NotFoundError("Portrait not found.")
        return portrait

    async def _require_resume(self, resume_id: UUID) -> ResumeVersion:
        resume = await self.repository.get_resume(resume_id)
        if resume is None:
            raise NotFoundError("Résumé version not found.")
        return resume

    async def _require_social_link(self, link_id: UUID) -> SocialLink:
        link = await self.repository.get_social_link(link_id)
        if link is None:
            raise NotFoundError("Social link not found.")
        return link

    async def _commit_conflict(self, message: str) -> None:
        try:
            await self.transaction.commit()
        except IntegrityError as exc:
            await self.transaction.rollback()
            raise ConflictError(message) from exc
