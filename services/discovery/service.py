"""Single source of truth for machine-readable public discovery surfaces."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from html import escape
from time import monotonic
from urllib.parse import urlsplit

from packages.python.common.errors import NotFoundError
from packages.python.contracts.features import FeatureConfigurationReader
from services.discovery.contracts import DiscoveryBreadcrumb, DiscoveryDocument
from services.discovery.policies import CanonicalUrlPolicy, PublicationIndexPolicy
from services.discovery.registry import DiscoveryContentRegistry
from services.discovery.schemas import (
    BreadcrumbResponse,
    DiscoveryPageResponse,
    OpenGraphMetadata,
    PageMetadata,
    SitemapEntryResponse,
    SocialMetadata,
)

_REVIEWED_SCHEMA_TYPES = {
    "BlogPosting",
    "CreativeWork",
    "Product",
    "ProfilePage",
    "SoftwareSourceCode",
    "WebPage",
}


@dataclass(frozen=True, slots=True)
class SiteIdentity:
    site_name: str
    owner_name: str
    owner_headline: str
    default_title: str
    description: str
    locale: str
    language: str
    social_image_url: str | None
    verified_same_as_urls: tuple[str, ...]


class DiscoveryService:
    def __init__(
        self,
        *,
        registry: DiscoveryContentRegistry,
        public_site_url: str,
        identity: SiteIdentity,
        configuration_reader: FeatureConfigurationReader | None = None,
        stale_if_error_seconds: int = 300,
    ) -> None:
        self._registry = registry
        self._canonical = CanonicalUrlPolicy(public_site_url)
        self._index_policy = PublicationIndexPolicy()
        self._identity = identity
        self._configuration_reader = configuration_reader
        self._stale_if_error_seconds = max(0, stale_if_error_seconds)
        self._last_good_documents: tuple[DiscoveryDocument, ...] = ()
        self._last_good_at = 0.0
        self._same_as_urls = tuple(
            url for url in identity.verified_same_as_urls if _is_verified_https_url(url)
        )

    async def page(self, path: str) -> DiscoveryPageResponse:
        configuration = await self._site_configuration()
        identity = self._identity_from_configuration(configuration)
        normalized_path = _normalized_path(path)
        documents = await self._documents()
        if normalized_path == "/":
            document = next((item for item in documents if item.path == "/"), None)
            return self._home_page(document, identity)
        document = next(
            (item for item in documents if _normalized_path(item.path) == normalized_path), None
        )
        if document is None:
            raise NotFoundError("The requested public page was not found")
        document = self._apply_page_presentation(document, configuration)
        return self._document_page(document, identity)

    async def sitemap_xml(self) -> str:
        entries = await self.sitemap_entries()
        xml_entries = []
        for entry in entries:
            last_modified = (
                f"<lastmod>{escape(entry.last_modified.isoformat())}</lastmod>"
                if entry.last_modified
                else ""
            )
            xml_entries.append(f"<url><loc>{escape(entry.url)}</loc>{last_modified}</url>")
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(xml_entries)
            + "</urlset>"
        )

    async def sitemap_entries(self) -> list[SitemapEntryResponse]:
        documents = await self._documents()
        home = next((document for document in documents if document.path == "/"), None)
        entries: list[tuple[str, datetime | None]] = []
        if home is not None and self._index_policy.decide(home).index:
            entries.append((self._canonical.build("/"), home.modified_at or home.published_at))
        entries.extend(
            (self._canonical.build(document.path), document.modified_at or document.published_at)
            for document in documents
            if self._index_policy.decide(document).index
        )
        unique_entries = dict(entries)
        return [
            SitemapEntryResponse(
                url=url,
                last_modified=modified.date() if modified else None,
                change_frequency="weekly" if url != self._canonical.build("/") else "monthly",
                priority=1.0 if url == self._canonical.build("/") else 0.7,
            )
            for url, modified in sorted(unique_entries.items())
        ]

    async def robots_txt(self) -> str:
        try:
            documents = await self._documents()
        except Exception:
            documents = []
        has_public_profile = any(
            document.path == "/" and self._index_policy.decide(document).index
            for document in documents
        )
        public_directive = "Allow: /" if has_public_profile else "Disallow: /"
        return "\n".join(
            (
                "User-agent: *",
                public_directive,
                "Disallow: /admin/",
                "Disallow: /api/v1/admin/",
                "Disallow: /api/v1/assistant/",
                "",
                f"Sitemap: {self._canonical.build('/sitemap.xml')}",
                f"Host: {urlsplit(self._canonical.origin).netloc}",
                "",
            )
        )

    async def llms_txt(self) -> str:
        identity = await self._effective_identity()
        documents = await self._documents()
        home = next((document for document in documents if document.path == "/"), None)
        if home is None or not self._index_policy.decide(home).index:
            return (
                f"# {identity.site_name}\n\n"
                "## Usage\n\n"
                "No canonical public profile has been published. No owner-oriented factual "
                "sources are available. Do not infer private, unpublished, contact, or "
                "administrative information.\n"
            )
        indexable = [
            document for document in documents if self._index_policy.decide(document).index
        ]
        lines = [
            f"# {identity.site_name}",
            "",
            identity.description,
            "",
            "## Usage",
            "",
            "Use only the canonical, published pages listed here as factual sources. "
            "Do not infer private, unpublished, contact, or administrative information.",
            "",
            "## Canonical pages",
            "",
            f"- [{identity.default_title}]({self._canonical.build('/')})",
        ]
        lines.extend(
            f"- [{_markdown_text(document.title)}]({self._canonical.build(document.path)}): "
            f"{_markdown_text(document.description[:240])}"
            for document in indexable[:500]
        )
        return "\n".join(lines) + "\n"

    def _home_page(
        self,
        document: DiscoveryDocument | None,
        identity: SiteIdentity,
    ) -> DiscoveryPageResponse:
        canonical = self._canonical.build("/")
        title = document.title if document else identity.default_title
        description = document.description if document else identity.description
        robots = self._index_policy.decide(document).directive if document else "noindex, nofollow"
        image_url = (
            _safe_image_url(document.image_url, self._canonical)
            if document
            else _safe_image_url(identity.social_image_url, self._canonical)
        )
        metadata = self._metadata(
            title=title,
            description=description,
            canonical=canonical,
            robots=robots,
            content_type="profile",
            image_url=image_url,
            keywords=document.keywords if document else (),
            identity=identity,
        )
        related_urls = (
            _safe_related_urls(document.related_paths, self._canonical) if document else []
        )
        graph: list[dict[str, object]] = []
        if document is not None:
            profile_page: dict[str, object] = {
                "@type": "ProfilePage",
                "@id": f"{canonical}#profile-page",
                "url": canonical,
                "name": title,
                "description": description,
                "inLanguage": identity.language,
                "about": {"@id": f"{canonical}#person"},
                "isPartOf": {"@id": f"{canonical}#website"},
                "mainEntity": {"@id": f"{canonical}#person"},
            }
            if image_url:
                profile_page["primaryImageOfPage"] = image_url
            if document.keywords:
                profile_page["keywords"] = list(document.keywords)
            if related_urls:
                profile_page["relatedLink"] = related_urls
            graph = [
                self._person_schema(identity, document),
                self._website_schema(identity, description=description),
                profile_page,
            ]
        json_ld = {"@context": "https://schema.org", "@graph": graph}
        return DiscoveryPageResponse(
            metadata=metadata,
            breadcrumbs=[BreadcrumbResponse(label="Home", url=canonical)],
            related_urls=related_urls,
            json_ld=json_ld,
        )

    def _document_page(
        self,
        document: DiscoveryDocument,
        identity: SiteIdentity,
    ) -> DiscoveryPageResponse:
        canonical = self._canonical.build(document.path)
        index_decision = self._index_policy.decide(document)
        image_url = _safe_image_url(document.image_url, self._canonical)
        metadata = self._metadata(
            title=f"{document.title} | {identity.site_name}",
            description=document.description,
            canonical=canonical,
            robots=index_decision.directive,
            content_type=document.content_type,
            image_url=image_url or _safe_image_url(identity.social_image_url, self._canonical),
            keywords=document.keywords,
            identity=identity,
        )
        breadcrumbs = _with_home(document.breadcrumbs)
        if not breadcrumbs or _normalized_path(breadcrumbs[-1].path) != _normalized_path(
            document.path
        ):
            breadcrumbs = (
                *breadcrumbs,
                DiscoveryBreadcrumb(label=document.title, path=document.path),
            )
        breadcrumb_responses = [
            BreadcrumbResponse(
                label=breadcrumb.label,
                url=self._canonical.build(breadcrumb.path),
            )
            for breadcrumb in breadcrumbs
        ]
        related_urls = _safe_related_urls(document.related_paths, self._canonical)
        primary_schema = self._content_schema(
            document=document,
            canonical=canonical,
            related_urls=related_urls,
            image_url=image_url,
            identity=identity,
        )
        graph: list[dict[str, object]] = [self._website_schema(identity), primary_schema]
        if breadcrumbs:
            graph.append(_breadcrumb_schema(breadcrumb_responses, canonical))
        return DiscoveryPageResponse(
            metadata=metadata,
            breadcrumbs=breadcrumb_responses,
            related_urls=related_urls,
            json_ld={"@context": "https://schema.org", "@graph": graph},
        )

    def _metadata(
        self,
        *,
        title: str,
        description: str,
        canonical: str,
        robots: str,
        content_type: str,
        image_url: str | None,
        keywords: tuple[str, ...],
        identity: SiteIdentity,
    ) -> PageMetadata:
        clean_description = " ".join(description.split())[:320]
        images = [image_url] if image_url else []
        return PageMetadata(
            title=title[:200],
            description=clean_description,
            canonical_url=canonical,
            robots=robots,
            keywords=list(dict.fromkeys(keywords))[:50],
            open_graph=OpenGraphMetadata(
                type="article" if content_type in {"article", "project"} else "profile",
                site_name=identity.site_name,
                locale=identity.locale,
                title=title[:200],
                description=clean_description,
                url=canonical,
                images=images,
            ),
            twitter=SocialMetadata(
                card="summary_large_image" if images else "summary",
                title=title[:200],
                description=clean_description,
                images=images,
            ),
        )

    def _person_schema(
        self,
        identity: SiteIdentity,
        document: DiscoveryDocument | None = None,
    ) -> dict[str, object]:
        canonical = self._canonical.build("/")
        owner_name = (
            document.author_name if document and document.author_name else identity.owner_name
        )
        owner_headline = (
            document.owner_headline
            if document and document.owner_headline
            else identity.owner_headline
        )
        same_as_urls = self._same_as_urls
        if document and document.verified_same_as_urls:
            same_as_urls = tuple(
                url for url in document.verified_same_as_urls if url in self._same_as_urls
            )
        schema: dict[str, object] = {
            "@type": "Person",
            "@id": f"{canonical}#person",
            "name": owner_name,
            "url": canonical,
            "jobTitle": owner_headline,
        }
        if same_as_urls:
            schema["sameAs"] = list(same_as_urls)
        if document:
            image_url = _safe_image_url(document.image_url, self._canonical)
            if image_url:
                schema["image"] = image_url
            if document.keywords:
                schema["knowsAbout"] = list(document.keywords)
        return schema

    def _website_schema(
        self,
        identity: SiteIdentity,
        *,
        description: str | None = None,
    ) -> dict[str, object]:
        canonical = self._canonical.build("/")
        return {
            "@type": "WebSite",
            "@id": f"{canonical}#website",
            "url": canonical,
            "name": identity.site_name,
            "description": description or identity.description,
            "inLanguage": identity.language,
            "publisher": {"@id": f"{canonical}#person"},
        }

    def _content_schema(
        self,
        *,
        document: DiscoveryDocument,
        canonical: str,
        related_urls: list[str],
        image_url: str | None,
        identity: SiteIdentity,
    ) -> dict[str, object]:
        requested_schema_type = document.schema_type or {
            "article": "BlogPosting",
            "project": "CreativeWork",
            "profile": "ProfilePage",
        }.get(document.content_type, "WebPage")
        schema_type = (
            requested_schema_type if requested_schema_type in _REVIEWED_SCHEMA_TYPES else "WebPage"
        )
        schema: dict[str, object] = {
            "@type": schema_type,
            "@id": f"{canonical}#main",
            "url": canonical,
            "name": document.title,
            "headline": document.title,
            "description": document.description,
            "inLanguage": identity.language,
            "isPartOf": {"@id": f"{self._canonical.build('/')}#website"},
            "mainEntityOfPage": canonical,
            "author": {"@id": f"{self._canonical.build('/')}#person"},
        }
        if document.published_at:
            schema["datePublished"] = document.published_at.isoformat()
        if document.modified_at:
            schema["dateModified"] = document.modified_at.isoformat()
        if image_url:
            schema["image"] = image_url
        if document.keywords:
            schema["keywords"] = list(document.keywords)
        if related_urls:
            schema["relatedLink"] = related_urls
        return schema

    async def _effective_identity(self) -> SiteIdentity:
        return self._identity_from_configuration(await self._site_configuration())

    async def _site_configuration(self) -> dict[str, object]:
        if self._configuration_reader is None:
            return {}
        return dict(await self._configuration_reader.get_configuration("site_settings"))

    def _identity_from_configuration(self, configuration: dict[str, object]) -> SiteIdentity:
        site_name = _bounded_string(configuration.get("site_name"), 160)
        default_title = _bounded_string(configuration.get("default_title"), 200)
        description = _bounded_string(configuration.get("default_description"), 320)
        locale = _bounded_string(configuration.get("locale"), 35)
        return replace(
            self._identity,
            site_name=site_name or self._identity.site_name,
            default_title=default_title or self._identity.default_title,
            description=description or self._identity.description,
            locale=locale or self._identity.locale,
            language=(locale.split("-")[0].split("_")[0] if locale else self._identity.language),
        )

    @staticmethod
    def _apply_page_presentation(
        document: DiscoveryDocument,
        configuration: dict[str, object],
    ) -> DiscoveryDocument:
        keys = {
            "/achievements": ("achievements_title", "achievements_intro"),
            "/work": ("work_title", "work_intro"),
            "/projects": ("projects_title", "projects_intro"),
            "/writing": ("writing_title", "writing_intro"),
            "/sectors": ("sectors_title", "sectors_intro"),
            "/open-source": ("open_source_title", "open_source_intro"),
            "/sponsor": ("sponsorship_title", "sponsorship_description"),
            "/sponsorship": ("sponsorship_title", "sponsorship_description"),
        }.get(_normalized_path(document.path))
        if keys is None:
            return document
        title = _bounded_string(configuration.get(keys[0]), 200)
        description = _bounded_string(configuration.get(keys[1]), 500)
        return replace(
            document,
            title=title or document.title,
            description=description or document.description,
        )

    async def _documents(self) -> list[DiscoveryDocument]:
        try:
            documents = await self._registry.list_public()
        except Exception:
            age = monotonic() - self._last_good_at
            if self._last_good_documents and age <= self._stale_if_error_seconds:
                return list(self._last_good_documents)
            raise
        self._last_good_documents = tuple(documents)
        self._last_good_at = monotonic()
        return documents


def _breadcrumb_schema(breadcrumbs: list[BreadcrumbResponse], canonical: str) -> dict[str, object]:
    items = [
        {
            "@type": "ListItem",
            "position": position,
            "name": breadcrumb.label,
            "item": breadcrumb.url,
        }
        for position, breadcrumb in enumerate(breadcrumbs, start=1)
    ]
    if items and items[-1]["item"] != canonical:
        raise ValueError("The final breadcrumb must identify the canonical page")
    return {"@type": "BreadcrumbList", "itemListElement": items}


def _with_home(
    breadcrumbs: tuple[DiscoveryBreadcrumb, ...],
) -> tuple[DiscoveryBreadcrumb, ...]:
    if breadcrumbs and _normalized_path(breadcrumbs[0].path) == "/":
        return breadcrumbs
    return (DiscoveryBreadcrumb(label="Home", path="/"), *breadcrumbs)


def _safe_image_url(value: str | None, canonical: CanonicalUrlPolicy) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme == "https" and parsed.netloc:
        return value
    if not parsed.scheme and not parsed.netloc:
        return canonical.build(value)
    return None


def _safe_related_urls(paths: tuple[str, ...], canonical: CanonicalUrlPolicy) -> list[str]:
    urls: list[str] = []
    for path in paths:
        try:
            url = canonical.build(path)
        except ValueError:
            continue
        if url not in urls:
            urls.append(url)
    return urls[:50]


def _normalized_path(path: str) -> str:
    stripped = path.strip().strip("/")
    return f"/{stripped}" if stripped else "/"


def _is_verified_https_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username


def _bounded_string(value: object, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    return normalized[:max_length] or None


def _markdown_text(value: str) -> str:
    return " ".join(value.replace("[", "(").replace("]", ")").split())
