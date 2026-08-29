from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.python.common.models import PublicationStatus
from services.identity.models import PortraitAsset, Profile, ResumeVersion, SocialLink


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _profile_load_options() -> tuple[Any, ...]:
        return (
            selectinload(Profile.portraits),
            selectinload(Profile.resume_versions),
            selectinload(Profile.social_links),
        )

    async def get_profile(self, profile_id: UUID) -> Profile | None:
        return cast(
            Profile | None,
            await self.session.scalar(
                select(Profile)
                .where(Profile.id == profile_id)
                .options(*self._profile_load_options())
            ),
        )

    async def get_profile_by_seed_key(self, seed_key: str) -> Profile | None:
        return cast(
            Profile | None,
            await self.session.scalar(select(Profile).where(Profile.seed_key == seed_key)),
        )

    async def get_public_profile(self) -> Profile | None:
        return cast(
            Profile | None,
            await self.session.scalar(
                select(Profile)
                .where(
                    Profile.status == PublicationStatus.PUBLISHED,
                    Profile.is_visible.is_(True),
                    Profile.archived_at.is_(None),
                )
                .options(*self._profile_load_options())
                .order_by(Profile.is_primary.desc(), Profile.updated_at.desc())
                .limit(1)
            ),
        )

    async def list_profiles(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        status: PublicationStatus | None = None,
    ) -> tuple[Sequence[Profile], int]:
        statement = select(Profile)
        if status is not None:
            statement = statement.where(Profile.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Profile.full_name.ilike(pattern),
                    Profile.headline.ilike(pattern),
                    Profile.short_bio.ilike(pattern),
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
        base = statement.options(*self._profile_load_options()).order_by(Profile.created_at)
        items = (await self.session.scalars(base.limit(limit).offset(offset))).unique().all()
        return items, total

    async def profile_count(self) -> int:
        return int((await self.session.scalar(select(func.count(Profile.id)))) or 0)

    async def has_primary_profile(self) -> bool:
        return bool(
            await self.session.scalar(
                select(Profile.id).where(Profile.is_primary.is_(True)).limit(1)
            )
        )

    async def has_primary_portrait(self, profile_id: UUID) -> bool:
        return bool(
            await self.session.scalar(
                select(PortraitAsset.id)
                .where(
                    PortraitAsset.profile_id == profile_id,
                    PortraitAsset.is_primary.is_(True),
                    PortraitAsset.is_active.is_(True),
                )
                .limit(1)
            )
        )

    def add_profile(self, profile: Profile) -> Profile:
        self.session.add(profile)
        return profile

    async def clear_primary_profiles(self, excluding: UUID | None = None) -> None:
        statement = update(Profile).where(Profile.is_primary.is_(True))
        if excluding:
            statement = statement.where(Profile.id != excluding)
        await self.session.execute(statement.values(is_primary=False))

    async def get_portrait(self, portrait_id: UUID) -> PortraitAsset | None:
        return await self.session.get(PortraitAsset, portrait_id)

    async def get_portrait_by_seed_key(self, seed_key: str) -> PortraitAsset | None:
        return cast(
            PortraitAsset | None,
            await self.session.scalar(
                select(PortraitAsset).where(PortraitAsset.seed_key == seed_key)
            ),
        )

    def add_portrait(self, portrait: PortraitAsset) -> PortraitAsset:
        self.session.add(portrait)
        return portrait

    async def clear_primary_portraits(
        self, profile_id: UUID, excluding: UUID | None = None
    ) -> None:
        statement = update(PortraitAsset).where(
            PortraitAsset.profile_id == profile_id,
            PortraitAsset.is_primary.is_(True),
        )
        if excluding:
            statement = statement.where(PortraitAsset.id != excluding)
        await self.session.execute(statement.values(is_primary=False))

    async def get_resume(self, resume_id: UUID) -> ResumeVersion | None:
        return await self.session.get(ResumeVersion, resume_id)

    async def get_resume_by_seed_key(self, seed_key: str) -> ResumeVersion | None:
        return cast(
            ResumeVersion | None,
            await self.session.scalar(
                select(ResumeVersion).where(ResumeVersion.seed_key == seed_key)
            ),
        )

    async def get_any_current_resume(self) -> ResumeVersion | None:
        return cast(
            ResumeVersion | None,
            await self.session.scalar(
                select(ResumeVersion).where(ResumeVersion.is_current.is_(True)).limit(1)
            ),
        )

    async def get_public_current_resume(self, profile_id: UUID) -> ResumeVersion | None:
        return cast(
            ResumeVersion | None,
            await self.session.scalar(
                select(ResumeVersion)
                .join(Profile, Profile.id == ResumeVersion.profile_id)
                .where(
                    ResumeVersion.profile_id == profile_id,
                    ResumeVersion.is_current.is_(True),
                    ResumeVersion.status == PublicationStatus.PUBLISHED,
                    ResumeVersion.is_visible.is_(True),
                    ResumeVersion.archived_at.is_(None),
                    Profile.status == PublicationStatus.PUBLISHED,
                    Profile.is_visible.is_(True),
                    Profile.archived_at.is_(None),
                )
                .limit(1)
            ),
        )

    def add_resume(self, resume: ResumeVersion) -> ResumeVersion:
        self.session.add(resume)
        return resume

    async def list_resumes(self, profile_id: UUID) -> Sequence[ResumeVersion]:
        return (
            await self.session.scalars(
                select(ResumeVersion)
                .where(ResumeVersion.profile_id == profile_id)
                .order_by(ResumeVersion.created_at.desc())
            )
        ).all()

    async def clear_current_resumes(self, excluding: UUID | None = None) -> None:
        statement = update(ResumeVersion).where(ResumeVersion.is_current.is_(True))
        if excluding:
            statement = statement.where(ResumeVersion.id != excluding)
        await self.session.execute(statement.values(is_current=False))

    async def get_social_link(self, link_id: UUID) -> SocialLink | None:
        return await self.session.get(SocialLink, link_id)

    async def get_social_link_by_seed_key(self, seed_key: str) -> SocialLink | None:
        return cast(
            SocialLink | None,
            await self.session.scalar(select(SocialLink).where(SocialLink.seed_key == seed_key)),
        )

    def add_social_link(self, link: SocialLink) -> SocialLink:
        self.session.add(link)
        return link

    async def delete_social_link(self, link: SocialLink) -> None:
        await self.session.delete(link)
