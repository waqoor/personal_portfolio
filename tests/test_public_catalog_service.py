from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from packages.python.common.settings import Settings
from services.assistant.contracts import PublishedContentDocument
from services.content.schemas import PublicArticleRead
from services.identity.schemas import ProfileRead
from services.portfolio.schemas import (
    CategoryRead,
    ExperienceRead,
    PublicMetricRead,
    PublicProjectRead,
    PublicSkillRead,
    PublicTestimonialRead,
    SectorRead,
    SkillSummary,
)
from services.public_catalog.service import (
    CanonicalPublicContentProvider,
    _document_relevance,
    _PublicSnapshot,
)

NOW = datetime(2026, 8, 28, tzinfo=UTC)


def test_catalog_relevance_prefers_an_explicit_content_type_intent() -> None:
    common = {
        "source_id": "source",
        "title": "Canonical verification",
        "excerpt": "Published verification evidence.",
        "canonical_url": "https://portfolio.example.com/",
        "published_at": NOW,
    }
    profile = PublishedContentDocument(content_type="profile", **common)  # type: ignore[arg-type]
    project = PublishedContentDocument(content_type="project", **common)  # type: ignore[arg-type]

    terms = {"verification", "project", "prove"}

    assert _document_relevance(project, terms) > _document_relevance(profile, terms)


def _published(entity_id: str) -> dict[str, object]:
    return {
        "id": UUID(entity_id),
        "created_at": NOW,
        "updated_at": NOW,
        "status": "published",
        "is_visible": True,
        "noindex": False,
        "published_at": NOW,
        "archived_at": None,
    }


def test_canonical_catalog_maps_only_public_contracts_into_ai_and_discovery_documents() -> None:
    category = CategoryRead.model_validate(
        {
            **_published("00000000-0000-0000-0000-000000000001"),
            "name": "Production systems",
            "slug": "production-systems",
            "description": "Reviewed production engineering work.",
            "color": None,
            "icon_key": None,
            "sort_order": 0,
        }
    )
    sector = SectorRead.model_validate(
        {
            **_published("00000000-0000-0000-0000-000000000002"),
            "name": "Infrastructure",
            "slug": "infrastructure",
            "description": "Infrastructure backed by published project evidence.",
            "color": None,
            "icon_key": None,
            "sort_order": 0,
            "project_count": 1,
        }
    )
    skill = PublicSkillRead.model_validate(
        {
            "id": "00000000-0000-0000-0000-000000000003",
            "updated_at": NOW,
            "published_at": NOW,
            "noindex": False,
            "name": "FastAPI",
            "slug": "fastapi",
            "description": "Typed HTTP services.",
            "icon_key": None,
            "proficiency_label": "Production",
            "years_experience": 5,
            "sort_order": 0,
            "category": category,
            "project_count": 1,
        }
    )
    skill_summary = SkillSummary(
        id=skill.id,
        name=skill.name,
        slug=skill.slug,
        icon_key=skill.icon_key,
    )
    project_id = UUID("00000000-0000-0000-0000-000000000004")
    metric = PublicMetricRead.model_validate(
        {
            **_published("00000000-0000-0000-0000-000000000005"),
            "project_id": project_id,
            "experience_id": None,
            "subject_label": None,
            "label": "Availability",
            "value": "99.9",
            "unit": "%",
            "context": "Measured over the reviewed production interval.",
            "public_evidence": None,
            "sort_order": 0,
        }
    )
    testimonial = PublicTestimonialRead.model_validate(
        {
            **_published("00000000-0000-0000-0000-000000000006"),
            "project_id": project_id,
            "experience_id": None,
            "subject_label": None,
            "quote": "The delivery was reliable and well documented.",
            "attribution_name": "Reviewed client",
            "attribution_title": "Engineering lead",
            "attribution_organization": "Example organization",
            "public_evidence": None,
            "sort_order": 0,
        }
    )
    project = PublicProjectRead.model_validate(
        {
            **_published(str(project_id)),
            "title": "Canonical platform",
            "slug": "canonical-platform",
            "summary": "A published FastAPI platform with reviewed reliability evidence.",
            "role": "Lead engineer",
            "start_date": date(2025, 1, 1),
            "end_date": None,
            "links": [],
            "repository_url": "https://github.com/example/canonical-platform",
            "live_url": None,
            "is_open_source": True,
            "nature": "software",
            "repository_metadata": None,
            "featured_rank": 1,
            "seo_title": None,
            "seo_description": None,
            "category": category,
            "skills": [skill_summary],
            "sectors": [sector],
            "media": [],
            "metrics": [metric],
            "description": "The service composes bounded public contracts.",
            "problem": "Private domain implementations must not leak.",
            "solution": "A dedicated public catalog owns cross-domain composition.",
            "architecture": "Factories expose only public reader protocols.",
            "features": ["Bounded aggregation"],
            "decisions": ["Public DTOs only"],
            "tradeoffs": ["Strict public projections"],
            "challenges": ["Cross-domain ownership"],
            "outcomes": ["Canonical sources"],
            "testimonials": [testimonial],
            "related_projects": [],
        }
    )
    experience = ExperienceRead.model_validate(
        {
            **_published("00000000-0000-0000-0000-000000000007"),
            "organization": "Example organization",
            "role": "Lead engineer",
            "location": None,
            "employment_type": "Full time",
            "start_date": date(2024, 1, 1),
            "end_date": None,
            "summary": "Built reviewed public systems.",
            "achievements": ["Shipped a canonical platform"],
            "sort_order": 0,
            "skills": [skill_summary],
            "sectors": [sector],
            "projects": [],
        }
    )
    article = PublicArticleRead.model_validate(
        {
            **_published("00000000-0000-0000-0000-000000000008"),
            "title": "Testing canonical boundaries",
            "slug": "testing-canonical-boundaries",
            "excerpt": "A reviewed explanation of public composition.",
            "body_markdown": "Public contracts keep private implementations private.",
            "topics": ["architecture"],
            "reading_minutes": 2,
            "seo_title": None,
            "seo_description": None,
            "hero_media": None,
            "related_articles": [],
        }
    )
    profile = ProfileRead.model_validate(
        {
            **_published("00000000-0000-0000-0000-000000000009"),
            "full_name": "Portfolio owner",
            "headline": "Production engineer",
            "short_bio": "Builds reviewed public systems.",
            "long_bio": "Works across product and infrastructure.",
            "public_location": "Riyadh",
            "availability_status": "selective",
            "availability_detail": None,
            "public_email": None,
            "primary_cta_label": None,
            "primary_cta_url": None,
            "secondary_cta_label": None,
            "secondary_cta_url": None,
            "is_primary": True,
            "portraits": [],
            "social_links": [],
        }
    )
    snapshot = _PublicSnapshot(
        profile=profile,
        categories=[category],
        sectors=[sector],
        skills=[skill],
        experiences=[experience],
        education=[],
        certifications=[],
        projects=[project],
        metrics=[metric],
        testimonials=[testimonial],
        articles=[article],
    )
    provider = CanonicalPublicContentProvider(
        identity_reader=None,  # type: ignore[arg-type]
        portfolio_reader=None,  # type: ignore[arg-type]
        content_reader=None,  # type: ignore[arg-type]
        settings=Settings(
            _env_file=None,
            environment="test",
            public_base_url="https://portfolio.example",
            auth_secret="test-auth-secret-with-at-least-32-characters",
            privacy_hash_secret="test-privacy-secret-with-at-least-32-characters",
        ),
    )

    assistant_documents = provider._assistant_documents(snapshot)
    discovery_documents = provider._discovery_documents(snapshot)

    by_source = {document.source_id: document for document in assistant_documents}
    assert by_source[f"project:{project_id}"].canonical_url == (
        "https://portfolio.example/projects/canonical-platform"
    )
    assert "Public DTOs only" in by_source[f"project:{project_id}"].excerpt
    assert "Bounded aggregation. Public DTOs only." in by_source[f"project:{project_id}"].excerpt
    assert by_source[f"article:{article.id}"].excerpt == (
        "A reviewed explanation of public composition. "
        "Public contracts keep private implementations private."
    )
    assert by_source[f"metric:{metric.id}"].canonical_url.endswith("/projects/canonical-platform")
    assert by_source[f"testimonial:{testimonial.id}"].content_type == "approved_testimonial"
    assert by_source[f"skill:{skill.id}"].canonical_url == "https://portfolio.example/"

    discovery_by_path = {document.path: document for document in discovery_documents}
    assert discovery_by_path["/projects/canonical-platform"].schema_type == ("SoftwareSourceCode")
    assert discovery_by_path["/projects/canonical-platform"].image_url is None
    assert discovery_by_path["/sectors/infrastructure"].related_paths == (
        "/projects",
        "/projects/canonical-platform",
    )
    assert {"/", "/projects", "/writing", "/sectors", "/open-source"} <= set(discovery_by_path)
    assert "/about" not in discovery_by_path
    assert "FastAPI" in discovery_by_path["/"].keywords
    assert "/work" in discovery_by_path["/"].related_paths
