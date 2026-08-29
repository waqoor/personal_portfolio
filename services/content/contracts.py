from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol

from packages.python.contracts.features import FeatureResolution
from services.content.schemas import PublicArticleRead, PublicArticleSummaryRead


class ContentPublicReader(Protocol):
    async def list_public_articles(self, limit: int = 20) -> list[PublicArticleSummaryRead]: ...

    async def search_public_articles(
        self, query: str, *, limit: int
    ) -> list[PublicArticleRead]: ...

    async def resolve_feature(self, key: str, *, default: bool) -> FeatureResolution: ...

    async def active_feature_configuration(self, key: str) -> dict[str, object]: ...


ContentPublicReaderFactory = Callable[[], AbstractAsyncContextManager[ContentPublicReader]]
