"""Typed metadata and semantic-navigation response contracts."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class OpenGraphMetadata(BaseModel):
    type: str
    site_name: str
    locale: str
    title: str
    description: str
    url: str
    images: list[str]


class SocialMetadata(BaseModel):
    card: str
    title: str
    description: str
    images: list[str]


class PageMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    canonical_url: str
    robots: str
    keywords: list[str]
    open_graph: OpenGraphMetadata
    twitter: SocialMetadata


class BreadcrumbResponse(BaseModel):
    label: str
    url: str


class DiscoveryPageResponse(BaseModel):
    metadata: PageMetadata
    breadcrumbs: list[BreadcrumbResponse]
    related_urls: list[str]
    json_ld: dict[str, object]


class SitemapEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    last_modified: date | None = None
    change_frequency: str | None = None
    priority: float | None = None


class MachineTextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
