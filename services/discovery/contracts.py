"""Public discovery read contracts implemented by content-owning services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DiscoveryBreadcrumb:
    label: str
    path: str


@dataclass(frozen=True, slots=True)
class DiscoveryDocument:
    source_id: str
    content_type: str
    path: str
    title: str
    description: str
    schema_type: str | None = None
    image_url: str | None = None
    published_at: datetime | None = None
    modified_at: datetime | None = None
    author_name: str | None = None
    keywords: tuple[str, ...] = ()
    breadcrumbs: tuple[DiscoveryBreadcrumb, ...] = ()
    related_paths: tuple[str, ...] = ()
    owner_headline: str | None = None
    verified_same_as_urls: tuple[str, ...] = ()
    is_published: bool = True
    is_public: bool = True
    is_hidden: bool = False
    is_archived: bool = False
    noindex: bool = False


class DiscoveryContentProvider(Protocol):
    """A service exposes public read DTOs, never private models/repositories."""

    async def list_for_discovery(self) -> list[DiscoveryDocument]: ...
