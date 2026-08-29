from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol

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


class PortfolioPublicReader(Protocol):
    async def list_public_categories(self, limit: int = 100) -> list[CategoryRead]: ...

    async def list_public_sectors(self, limit: int = 100) -> list[SectorRead]: ...

    async def list_public_skills(self, limit: int = 100) -> list[PublicSkillRead]: ...

    async def list_public_experiences(self, limit: int = 20) -> list[ExperienceRead]: ...

    async def list_public_education(self, limit: int = 20) -> list[EducationRead]: ...

    async def list_public_certifications(self, limit: int = 20) -> list[CertificationRead]: ...

    async def list_public_projects(
        self, limit: int = 20, *, featured_only: bool = False
    ) -> list[PublicProjectSummaryRead]: ...

    async def search_public_projects(
        self, query: str, *, limit: int
    ) -> list[PublicProjectRead]: ...

    async def list_public_metrics(self, limit: int = 100) -> list[PublicMetricRead]: ...

    async def list_public_testimonials(self, limit: int = 100) -> list[PublicTestimonialRead]: ...


PortfolioPublicReaderFactory = Callable[[], AbstractAsyncContextManager[PortfolioPublicReader]]
