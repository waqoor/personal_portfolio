from __future__ import annotations

from datetime import UTC, datetime

import pytest

from packages.python.common.errors import NotFoundError
from services.discovery.contracts import DiscoveryBreadcrumb, DiscoveryDocument
from services.discovery.policies import CanonicalUrlPolicy
from services.discovery.registry import DiscoveryContentRegistry
from services.discovery.service import DiscoveryService, SiteIdentity


class DiscoveryProvider:
    def __init__(self, documents: list[DiscoveryDocument]) -> None:
        self.documents = documents

    async def list_for_discovery(self) -> list[DiscoveryDocument]:
        return self.documents


class FailingAfterWarmupProvider(DiscoveryProvider):
    def __init__(self, documents: list[DiscoveryDocument]) -> None:
        super().__init__(documents)
        self.fail = False

    async def list_for_discovery(self) -> list[DiscoveryDocument]:
        if self.fail:
            raise RuntimeError("transient discovery source failure")
        return await super().list_for_discovery()


class ConfigurationReader:
    def __init__(self, configuration: dict[str, object]) -> None:
        self.configuration = configuration

    async def get_configuration(self, key: str) -> dict[str, object]:
        assert key == "site_settings"
        return self.configuration


def _document(**changes: object) -> DiscoveryDocument:
    values: dict[str, object] = {
        "source_id": "project-1",
        "content_type": "project",
        "schema_type": "SoftwareSourceCode",
        "path": "/projects/platform",
        "title": "Production platform",
        "description": "A verified production engineering case study.",
        "image_url": "/media/platform.png",
        "published_at": datetime(2026, 8, 1, tzinfo=UTC),
        "modified_at": datetime(2026, 8, 20, tzinfo=UTC),
        "keywords": ("FastAPI", "PostgreSQL"),
        "breadcrumbs": (DiscoveryBreadcrumb(label="Projects", path="/projects"),),
        "related_paths": ("/articles/platform-notes", "https://evil.invalid/path"),
    }
    values.update(changes)
    return DiscoveryDocument(**values)  # type: ignore[arg-type]


def _service(
    documents: list[DiscoveryDocument],
    *,
    configuration: dict[str, object] | None = None,
) -> DiscoveryService:
    return DiscoveryService(
        registry=DiscoveryContentRegistry((DiscoveryProvider(documents),)),
        public_site_url="https://portfolio.example",
        configuration_reader=(
            ConfigurationReader(configuration) if configuration is not None else None
        ),
        identity=SiteIdentity(
            site_name="Yazeed Hasan",
            owner_name="Yazeed Hasan",
            owner_headline="AI, Software, Data & Infrastructure Builder",
            default_title="Yazeed Hasan — Portfolio",
            description="Published professional portfolio.",
            locale="en_US",
            language="en",
            social_image_url="https://portfolio.example/social.png",
            verified_same_as_urls=(
                "https://github.com/verified-owner",
                "http://unverified.invalid/profile",
            ),
        ),
    )


@pytest.mark.asyncio
async def test_dynamic_project_metadata_and_json_ld_are_canonical() -> None:
    page = await _service([_document()]).page("/projects/platform")

    assert page.metadata.canonical_url == "https://portfolio.example/projects/platform"
    assert page.metadata.open_graph.url == page.metadata.canonical_url
    assert page.metadata.open_graph.images == ["https://portfolio.example/media/platform.png"]
    assert page.metadata.twitter.card == "summary_large_image"
    graph = page.json_ld["@graph"]
    assert isinstance(graph, list)
    assert any(item.get("@type") == "SoftwareSourceCode" for item in graph)
    assert any(item.get("@type") == "BreadcrumbList" for item in graph)
    assert [breadcrumb.label for breadcrumb in page.breadcrumbs] == [
        "Home",
        "Projects",
        "Production platform",
    ]
    assert page.related_urls == ["https://portfolio.example/articles/platform-notes"]


@pytest.mark.asyncio
async def test_home_schema_exposes_only_verified_https_same_as() -> None:
    page = await _service(
        [
            _document(
                source_id="profile",
                content_type="profile",
                schema_type="ProfilePage",
                path="/",
                title="Published profile",
                image_url="/media/profile.png",
                keywords=("Enterprise AI", "MLOps", "Data platforms"),
                related_paths=("/work", "/projects", "https://evil.invalid/path"),
            )
        ]
    ).page("/")
    graph = page.json_ld["@graph"]
    assert isinstance(graph, list)
    person = next(item for item in graph if item.get("@type") == "Person")
    assert person["sameAs"] == ["https://github.com/verified-owner"]
    assert person["image"] == "https://portfolio.example/media/profile.png"
    assert person["knowsAbout"] == ["Enterprise AI", "MLOps", "Data platforms"]
    assert any(item.get("@type") == "WebSite" for item in graph)
    profile_page = next(item for item in graph if item.get("@type") == "ProfilePage")
    assert profile_page["primaryImageOfPage"] == "https://portfolio.example/media/profile.png"
    assert profile_page["keywords"] == ["Enterprise AI", "MLOps", "Data platforms"]
    assert profile_page["relatedLink"] == [
        "https://portfolio.example/work",
        "https://portfolio.example/projects",
    ]


@pytest.mark.asyncio
async def test_persisted_site_settings_update_metadata_without_changing_origin() -> None:
    service = _service(
        [
            _document(
                source_id="profile",
                content_type="profile",
                schema_type="ProfilePage",
                path="/",
                title="Published profile",
            )
        ],
        configuration={
            "site_name": "  Configured   Portfolio  ",
            "default_title": "Configured title",
            "default_description": "Configured discovery description.",
            "locale": "ar_SA",
            "public_base_url": "https://attacker.invalid",
            "owner_name": "Untrusted owner override",
        },
    )

    page = await service.page("/")
    llms = await service.llms_txt()

    assert page.metadata.title == "Published profile"
    assert page.metadata.canonical_url == "https://portfolio.example/"
    assert page.metadata.open_graph.site_name == "Configured Portfolio"
    assert page.metadata.open_graph.locale == "ar_SA"
    assert page.metadata.description == "A verified production engineering case study."
    graph = page.json_ld["@graph"]
    assert isinstance(graph, list)
    person = next(item for item in graph if item.get("@type") == "Person")
    assert person["name"] == "Yazeed Hasan"
    assert "# Configured Portfolio" in llms
    assert "attacker.invalid" not in llms


@pytest.mark.asyncio
async def test_collection_discovery_metadata_uses_the_same_persisted_page_presentation() -> None:
    service = _service(
        [
            _document(
                source_id="projects-collection",
                content_type="collection",
                schema_type="WebPage",
                path="/projects",
                title="Stale hard-coded title",
                description="Stale hard-coded description.",
            )
        ],
        configuration={
            "site_name": "Configured Portfolio",
            "projects_title": "Reviewed project archive",
            "projects_intro": "Configured case-study introduction shared by UI and discovery.",
        },
    )

    page = await service.page("/projects")

    assert page.metadata.title == "Reviewed project archive | Configured Portfolio"
    assert page.metadata.description == (
        "Configured case-study introduction shared by UI and discovery."
    )
    graph = page.json_ld["@graph"]
    assert isinstance(graph, list)
    document = next(item for item in graph if item.get("@type") == "WebPage")
    assert document["name"] == "Reviewed project archive"


@pytest.mark.asyncio
async def test_sponsorship_discovery_uses_the_same_canonical_presentation_as_the_page() -> None:
    service = _service(
        [
            _document(
                source_id="engagement:sponsorship",
                content_type="webpage",
                schema_type="WebPage",
                path="/sponsor",
                title="Stale sponsorship title",
                description="Stale sponsorship description.",
                breadcrumbs=(DiscoveryBreadcrumb(label="Sponsor", path="/sponsor"),),
            )
        ],
        configuration={
            "site_name": "Configured Portfolio",
            "sponsorship_title": "Transparent public-work sponsorship",
            "sponsorship_description": (
                "Canonical sponsorship copy shared by page content and discovery metadata."
            ),
        },
    )

    page = await service.page("/sponsor")

    assert page.metadata.title == ("Transparent public-work sponsorship | Configured Portfolio")
    assert page.metadata.description == (
        "Canonical sponsorship copy shared by page content and discovery metadata."
    )
    graph = page.json_ld["@graph"]
    assert isinstance(graph, list)
    document = next(item for item in graph if item.get("@type") == "WebPage")
    assert document["name"] == "Transparent public-work sponsorship"


@pytest.mark.asyncio
async def test_clean_site_is_conservatively_unavailable_to_indexers() -> None:
    service = _service([])

    page = await service.page("/")
    sitemap = await service.sitemap_entries()
    llms = await service.llms_txt()
    robots = await service.robots_txt()

    assert page.metadata.robots == "noindex, nofollow"
    assert page.json_ld["@graph"] == []
    assert sitemap == []
    assert "No canonical public profile" in llms
    assert "Disallow: /" in robots


@pytest.mark.asyncio
async def test_sitemap_llms_and_index_policy_share_publication_authority() -> None:
    service = _service(
        [
            _document(
                source_id="profile",
                content_type="profile",
                schema_type="ProfilePage",
                path="/",
                title="Published profile",
            ),
            _document(),
            _document(
                source_id="article",
                content_type="article",
                path="/articles/public",
                title="Public article",
            ),
            _document(source_id="draft", path="/projects/draft", is_published=False),
            _document(source_id="hidden", path="/projects/hidden", is_hidden=True),
            _document(source_id="noindex", path="/projects/noindex", noindex=True),
            _document(source_id="archived", path="/projects/archived", is_archived=True),
        ]
    )

    sitemap = await service.sitemap_xml()
    llms = await service.llms_txt()
    assert "https://portfolio.example/projects/platform" in sitemap
    assert "https://portfolio.example/articles/public" in sitemap
    assert "draft" not in sitemap
    assert "hidden" not in sitemap
    assert "noindex" not in sitemap
    assert "archived" not in sitemap
    assert "Public article" in llms
    assert "/projects/noindex" not in llms


@pytest.mark.asyncio
async def test_transient_source_failure_serves_bounded_last_known_good_documents() -> None:
    provider = FailingAfterWarmupProvider(
        [
            _document(
                source_id="profile",
                content_type="profile",
                schema_type="ProfilePage",
                path="/",
                title="Published profile",
            ),
            _document(),
        ]
    )
    service = DiscoveryService(
        registry=DiscoveryContentRegistry((provider,)),
        public_site_url="https://portfolio.example",
        stale_if_error_seconds=300,
        identity=SiteIdentity(
            site_name="Yazeed Hasan",
            owner_name="Yazeed Hasan",
            owner_headline="AI, Software, Data & Infrastructure Builder",
            default_title="Yazeed Hasan - Portfolio",
            description="Published professional portfolio.",
            locale="en_US",
            language="en",
            social_image_url="https://portfolio.example/social.png",
            verified_same_as_urls=("https://github.com/verified-owner",),
        ),
    )

    warm_page = await service.page("/projects/platform")
    provider.fail = True

    cached_page = await service.page("/projects/platform")
    sitemap = await service.sitemap_xml()
    llms = await service.llms_txt()

    assert cached_page == warm_page
    assert "https://portfolio.example/projects/platform" in sitemap
    assert "Production platform" in llms


@pytest.mark.asyncio
async def test_noindex_page_stays_public_but_is_not_indexable() -> None:
    page = await _service([_document(noindex=True)]).page("/projects/platform")
    assert page.metadata.robots == "noindex, nofollow"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"is_published": False},
        {"is_public": False},
        {"is_hidden": True},
        {"is_archived": True},
    ],
)
async def test_non_public_lifecycle_states_cannot_resolve_discovery_pages(
    changes: dict[str, object],
) -> None:
    with pytest.raises(NotFoundError):
        await _service([_document(**changes)]).page("/projects/platform")


def test_canonical_policy_rejects_external_query_and_traversal() -> None:
    policy = CanonicalUrlPolicy("https://portfolio.example")
    with pytest.raises(ValueError):
        policy.build("https://evil.invalid/path")
    with pytest.raises(ValueError):
        policy.build("/projects/../admin")
    with pytest.raises(ValueError):
        policy.build("/projects/%2e%2e/admin")
    with pytest.raises(ValueError):
        policy.build("/project?preview=true")
