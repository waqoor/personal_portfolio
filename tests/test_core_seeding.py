from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select

from apps.api.seed import SeedManifest, run_seed
from apps.api.seed_importers import import_json_resume, import_linkedin_export
from packages.python.clients.database import DatabaseClient
from packages.python.common.models import PublicationStatus
from packages.python.common.settings import Settings
from services.content.models import Article, MediaAsset, NavigationItem
from services.identity.models import PortraitAsset, Profile, ResumeVersion, SocialLink
from services.portfolio.models import ImpactMetric, Project, ProjectNature
from services.portfolio.models import Testimonial as PortfolioTestimonial


def _manifest() -> SeedManifest:
    return SeedManifest.model_validate(
        {
            "schema_version": 1,
            "source": "curated",
            "identity": {
                "profiles": [
                    {
                        "seed_key": "profile.main",
                        "payload": {
                            "full_name": "Yazeed Hasan",
                            "headline": "Initial seeded headline",
                            "short_bio": "Seeded biography that an administrator may edit.",
                            "is_primary": True,
                            "status": "published",
                        },
                    }
                ],
                "social_links": [
                    {
                        "seed_key": "social.github",
                        "profile_seed_key": "profile.main",
                        "payload": {
                            "platform": "github",
                            "label": "GitHub",
                            "url": "https://github.com/example",
                            "sort_order": 1,
                        },
                    }
                ],
                "portraits": [
                    {
                        "seed_key": "portrait.main",
                        "profile_seed_key": "profile.main",
                        "file": "portrait.png",
                        "media_type": "image/png",
                        "alt_text": "Seeded professional portrait",
                        "make_primary": True,
                    }
                ],
                "resume_versions": [
                    {
                        "seed_key": "resume.2026-v1",
                        "profile_seed_key": "profile.main",
                        "file": "resume.pdf",
                        "version_label": "2026 v1",
                        "status": "published",
                        "make_current": True,
                    }
                ],
            },
            "portfolio": {
                "categories": [
                    {
                        "seed_key": "category.platforms",
                        "payload": {
                            "name": "Platforms",
                            "slug": "platforms",
                            "description": "Production platform engineering.",
                            "status": "published",
                        },
                    }
                ],
                "projects": [
                    {
                        "seed_key": "project.core-platform",
                        "category_seed_key": "category.platforms",
                        "payload": {
                            "title": "Core Platform",
                            "slug": "core-platform",
                            "summary": "A seeded project that remains editable.",
                            "nature": "software",
                            "featured_rank": 1,
                            "status": "published",
                        },
                    }
                ],
                "metrics": [
                    {
                        "seed_key": "metric.core-throughput",
                        "project_seed_key": "project.core-platform",
                        "payload": {
                            "label": "Throughput",
                            "value": "2x",
                            "context": "Imported evidence awaiting explicit approval.",
                            "evidence": {
                                "kind": "document_reference",
                                "visibility": "private_review",
                                "reference_text": "Resume evidence line 12",
                                "provenance": "Curated resume import",
                                "captured_at": "2026-08-01",
                            },
                            "status": "published",
                        },
                    }
                ],
                "testimonials": [
                    {
                        "seed_key": "testimonial.core-platform",
                        "project_seed_key": "project.core-platform",
                        "payload": {
                            "quote": "A source-backed imported testimonial.",
                            "attribution_name": "Verified Reference",
                            "evidence": {
                                "kind": "document_reference",
                                "visibility": "private_review",
                                "reference_text": "LinkedIn recommendation export",
                                "provenance": "Curated LinkedIn export",
                                "captured_at": "2026-08-01",
                            },
                            "status": "published",
                        },
                    }
                ],
            },
            "content": {
                "media": [
                    {
                        "seed_key": "media.article-hero",
                        "file": "article-image.png",
                        "media_type": "image/png",
                        "metadata": {
                            "alt_text": "Seeded article architecture diagram",
                            "caption": "A deterministic seeded media fixture.",
                        },
                        "status": "published",
                    }
                ],
                "articles": [
                    {
                        "seed_key": "article.seed-safety",
                        "hero_media_seed_key": "media.article-hero",
                        "payload": {
                            "title": "Seed safety",
                            "slug": "seed-safety",
                            "excerpt": "Canonical content seeding with managed media.",
                            "body_markdown": (
                                "# Seed safety\n\nContent remains canonical and idempotent."
                            ),
                            "topics": ["seeding", "operations"],
                            "status": "published",
                        },
                    }
                ],
                "features": [
                    {
                        "seed_key": "feature.work-enabled",
                        "payload": {"key": "work.enabled", "enabled": True},
                    }
                ],
                "homepage_sections": [
                    {
                        "seed_key": "section.selected-work",
                        "payload": {
                            "section_type": "selected_work",
                            "position": 1,
                            "feature_key": "work.enabled",
                            "status": "published",
                        },
                    }
                ],
                "navigation": [
                    {
                        "seed_key": "navigation.writing",
                        "payload": {
                            "label": "Writing",
                            "href": "/writing",
                            "location": "header",
                            "sort_order": 3,
                            "status": "published",
                        },
                    }
                ],
            },
        }
    )


def _settings(database: DatabaseClient, storage_root: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_url=str(database.engine.url),
        storage_root=storage_root,
        auth_secret="test-auth-secret-with-at-least-32-characters",
        privacy_hash_secret="test-privacy-secret-with-at-least-32-characters",
    )


@pytest.mark.asyncio
async def test_seed_is_idempotent_preserves_admin_edits_and_requires_approval(
    database_client: DatabaseClient,
    tmp_path: Path,
    png_bytes: bytes,
) -> None:
    (tmp_path / "resume.pdf").write_bytes(b"%PDF-1.7\nseeded resume\n%%EOF")
    (tmp_path / "portrait.png").write_bytes(png_bytes)
    (tmp_path / "article-image.png").write_bytes(png_bytes)
    settings = _settings(database_client, tmp_path / "media")
    manifest = _manifest()

    first = await run_seed(
        manifest,
        manifest_directory=tmp_path,
        settings=settings,
    )
    assert first.total_created == 13
    assert first.total_skipped == 0

    async with database_client.session_factory() as session:
        profile = await session.scalar(select(Profile).where(Profile.seed_key == "profile.main"))
        project = await session.scalar(
            select(Project).where(Project.seed_key == "project.core-platform")
        )
        metric = await session.scalar(
            select(ImpactMetric).where(ImpactMetric.seed_key == "metric.core-throughput")
        )
        testimonial = await session.scalar(
            select(PortfolioTestimonial).where(
                PortfolioTestimonial.seed_key == "testimonial.core-platform"
            )
        )
        resume = await session.scalar(
            select(ResumeVersion).where(ResumeVersion.seed_key == "resume.2026-v1")
        )
        portrait = await session.scalar(
            select(PortraitAsset).where(PortraitAsset.seed_key == "portrait.main")
        )
        social_link = await session.scalar(
            select(SocialLink).where(SocialLink.seed_key == "social.github")
        )
        article = await session.scalar(
            select(Article).where(Article.seed_key == "article.seed-safety")
        )
        article_media = await session.scalar(
            select(MediaAsset).where(MediaAsset.seed_key == "media.article-hero")
        )
        navigation = await session.scalar(
            select(NavigationItem).where(NavigationItem.seed_key == "navigation.writing")
        )
        assert profile is not None
        assert project is not None
        assert metric is not None
        assert testimonial is not None
        assert resume is not None
        assert portrait is not None
        assert social_link is not None
        assert article is not None
        assert article_media is not None
        assert navigation is not None
        assert metric.project_id == project.id
        assert testimonial.project_id == project.id
        assert metric.is_approved is False
        assert testimonial.is_approved is False
        assert resume.is_current is True
        assert portrait.is_primary is True
        assert social_link.profile_id == profile.id
        assert project.nature is ProjectNature.SOFTWARE
        assert article.hero_media_id == article_media.id
        assert article_media.caption == "A deterministic seeded media fixture."
        assert navigation.location.value == "header"
        profile.headline = "Administrator-authored headline"
        project.title = "Administrator-authored project title"
        project.status = PublicationStatus.HIDDEN
        project.is_visible = False
        await session.commit()

    second = await run_seed(
        manifest,
        manifest_directory=tmp_path,
        settings=settings,
    )
    assert second.total_created == 0
    assert second.total_skipped == 13

    async with database_client.session_factory() as session:
        profile = await session.scalar(select(Profile).where(Profile.seed_key == "profile.main"))
        project = await session.scalar(
            select(Project).where(Project.seed_key == "project.core-platform")
        )
        assert profile and project
        assert profile.headline == "Administrator-authored headline"
        assert project.title == "Administrator-authored project title"
        assert project.status is PublicationStatus.HIDDEN
        assert project.is_visible is False


def test_seed_manifest_rejects_duplicate_keys_and_natural_identities() -> None:
    raw = _manifest().model_dump(mode="json")
    raw["portfolio"]["projects"].append(raw["portfolio"]["projects"][0])
    with pytest.raises(PydanticValidationError):
        SeedManifest.model_validate(raw)

    raw = _manifest().model_dump(mode="json")
    duplicate_slug = {
        **raw["portfolio"]["projects"][0],
        "seed_key": "project.different-key",
    }
    raw["portfolio"]["projects"].append(duplicate_slug)
    with pytest.raises(PydanticValidationError):
        SeedManifest.model_validate(raw)


def test_seed_metric_can_use_seed_relationship_without_fake_subject_label() -> None:
    manifest = _manifest()
    metric = manifest.portfolio.metrics[0]
    assert metric.project_seed_key == "project.core-platform"
    assert metric.payload.project_id is None
    assert metric.payload.subject_label is None


def test_json_resume_import_is_bounded_draft_canonical_and_deterministic(
    tmp_path: Path,
) -> None:
    resume_pdf = tmp_path / "owner-resume.pdf"
    resume_pdf.write_bytes(b"%PDF-1.7\n/Type /Page\n%%EOF")
    source = tmp_path / "resume.json"
    source.write_text(
        json.dumps(
            {
                "basics": {
                    "name": "Imported Owner",
                    "label": "Platform Engineer",
                    "summary": "A source-authored biography.",
                    "email": "owner@example.com",
                    "url": "https://example.com",
                    "profiles": [
                        {
                            "network": "GitHub",
                            "username": "owner",
                            "url": "https://github.com/owner",
                        }
                    ],
                },
                "skills": [{"name": "Languages", "keywords": ["Python", "Rust"]}],
                "work": [
                    {
                        "name": "Example Co",
                        "position": "Engineer",
                        "startDate": "2024-01",
                        "summary": "Built reviewed systems.",
                        "highlights": ["Reduced a measured latency after validation."],
                    }
                ],
                "projects": [
                    {
                        "name": "Canonical Import",
                        "description": "A project imported for owner review.",
                        "keywords": ["Python"],
                        "url": "https://example.com/project",
                    }
                ],
                "x-portfolio-resume": {
                    "file": "owner-resume.pdf",
                    "version_label": "Imported 2026",
                    "download_name": "../unsafe owner resume.pdf",
                },
            }
        ),
        encoding="utf-8",
    )

    first = import_json_resume(source, manifest_directory=tmp_path)
    second = import_json_resume(source, manifest_directory=tmp_path)
    manifest = SeedManifest.model_validate(first.manifest)

    assert first.manifest == second.manifest
    assert manifest.source.value == "resume"
    assert manifest.review is not None
    assert manifest.review.publication_policy == "draft_review_required"
    assert manifest.identity.profiles[0].payload.status is PublicationStatus.DRAFT
    assert manifest.identity.profiles[0].payload.noindex is True
    assert manifest.identity.resume_versions[0].status is PublicationStatus.DRAFT
    assert manifest.identity.resume_versions[0].make_current is False
    assert all(item.payload.status is PublicationStatus.DRAFT for item in manifest.portfolio.skills)
    assert all(
        item.payload.status is PublicationStatus.DRAFT for item in manifest.portfolio.projects
    )
    assert manifest.portfolio.projects[0].skill_seed_keys == [manifest.portfolio.skills[0].seed_key]


def test_linkedin_zip_import_maps_supported_csvs_and_rejects_unsafe_archives(
    tmp_path: Path,
) -> None:
    source = tmp_path / "linkedin.zip"
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "Basic_LinkedInDataExport/Profile.csv",
            "First Name,Last Name,Headline,Summary,Geo Location\n"
            'Imported,Owner,"Senior Engineer","Reviewed source summary","Riyadh"\n',
        )
        archive.writestr("Skills.csv", "Name\nPython\n")
        archive.writestr(
            "Positions.csv",
            "Company Name,Title,Description,Location,Started On,Finished On\n"
            'Example Co,Engineer,"Built systems",Riyadh,Jan 2023,Dec 2024\n',
        )
        archive.writestr(
            "Recommendations Received.csv",
            "First Name,Last Name,Job Title,Company,Text\n"
            'Reviewer,One,Director,Example Co,"A source-authored recommendation."\n',
        )

    imported = import_linkedin_export(source)
    manifest = SeedManifest.model_validate(imported.manifest)
    assert manifest.source.value == "linkedin"
    assert manifest.identity.profiles[0].payload.status is PublicationStatus.DRAFT
    assert manifest.portfolio.experiences[0].payload.start_date.isoformat() == "2023-01-01"
    assert manifest.portfolio.experiences[0].payload.end_date is not None
    assert manifest.portfolio.testimonials[0].payload.status is PublicationStatus.DRAFT
    assert manifest.portfolio.testimonials[0].payload.evidence is None

    unsafe = tmp_path / "unsafe-linkedin.zip"
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("../Profile.csv", "First Name,Last Name\nUnsafe,Archive\n")
    with pytest.raises(ValueError, match="unsafe member path"):
        import_linkedin_export(unsafe)


def test_imported_sources_require_matching_provenance_and_draft_state() -> None:
    raw = {
        "schema_version": 1,
        "source": "resume",
        "identity": {},
        "portfolio": {},
        "content": {},
    }
    with pytest.raises(PydanticValidationError, match="bounded importer provenance"):
        SeedManifest.model_validate(raw)
