from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import httpx
import pytest
from sqlalchemy import event, func, select, update

from apps.api.auth.models import AdminRole, LoginAttempt
from apps.api.auth.repository import AuthRepository
from apps.api.auth.schemas import CreateAdminInput
from apps.api.auth.service import AuthService
from apps.api.main import create_app
from packages.python.clients.ai import AIGenerationRequest, AIProviderResponse
from packages.python.clients.database import DatabaseClient
from packages.python.clients.email import (
    ContactNotification,
    EmailDeliveryResult,
    SystemEmail,
)
from packages.python.clients.repository_metadata import (
    RepositoryMetadataProviderError,
    RepositoryMetadataResult,
)
from packages.python.common.rate_limit import RateLimitBucket
from packages.python.common.repository import SQLAlchemyTransactionManager
from packages.python.common.settings import Settings
from services.content.models import FeatureSetting, HomepageSection, HomepageSectionType
from services.identity.models import ResumeVersion
from services.portfolio.models import RepositoryMetadataSnapshot


@dataclass(slots=True)
class CoreAPI:
    client: httpx.AsyncClient
    csrf: str
    settings: Settings
    repository_client: FakeRepositoryMetadataClient

    @property
    def mutation_headers(self) -> dict[str, str]:
        return {self.settings.csrf_header_name: self.csrf}


class FakeRepositoryMetadataClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.results: list[RepositoryMetadataResult | RepositoryMetadataProviderError] = []

    async def fetch(
        self, repository_url: str, *, etag: str | None = None
    ) -> RepositoryMetadataResult:
        self.calls.append((repository_url, etag))
        result = (
            self.results.pop(0)
            if self.results
            else RepositoryMetadataResult(
                provider="github",
                repository_identity="example/source-project",
                language="Python",
                stars=42,
                forks=7,
                fetched_at=datetime.now(UTC),
                etag='"source-v1"',
            )
        )
        if isinstance(result, RepositoryMetadataProviderError):
            raise result
        return result

    async def close(self) -> None:
        return None


class SuccessfulEmailClient:
    def __init__(self) -> None:
        self.notifications: list[ContactNotification] = []

    async def send_contact_notification(
        self, notification: ContactNotification
    ) -> EmailDeliveryResult:
        self.notifications.append(notification)
        return EmailDeliveryResult(provider_message_id=f"sent-{len(self.notifications)}")

    async def send_system_email(self, message: SystemEmail) -> EmailDeliveryResult:
        del message
        return EmailDeliveryResult(provider_message_id="system-sent")

    async def health_check(self) -> bool:
        return True

    async def close(self) -> None:
        return None


class AvailableAIClient:
    async def generate(self, request: AIGenerationRequest) -> AIProviderResponse:
        del request
        return AIProviderResponse(
            content='{"claims": [{"text": "No verified answer.", "source_ids": []}]}',
            model="test-model",
        )

    async def health_check(self) -> bool:
        return True

    async def close(self) -> None:
        return None


def _settings(database: DatabaseClient, storage_root: Path, **changes: Any) -> Settings:
    values: dict[str, Any] = {
        "_env_file": None,
        "environment": "test",
        "database_url": str(database.engine.url),
        "storage_root": storage_root,
        "public_base_url": "https://portfolio.example",
        "api_public_url": "https://api.portfolio.example",
        "allowed_origins": ["https://portfolio.example"],
        "allowed_hosts": ["testserver"],
        "auth_secret": "test-auth-secret-with-at-least-32-characters",
        "privacy_hash_secret": "test-privacy-secret-with-at-least-32-characters",
        "contact_enabled": False,
        "sponsorship_enabled": False,
        "assistant_enabled": False,
        "featured_project_limit": 3,
    }
    values.update(changes)
    return Settings(**values)


async def _create_admin(
    app: Any,
    database: DatabaseClient,
    *,
    email: str = "owner@example.com",
    display_name: str = "Portfolio Owner",
    role: AdminRole = AdminRole.OWNER,
) -> None:
    async with database.session_factory() as session:
        service = AuthService(
            AuthRepository(session),
            SQLAlchemyTransactionManager(session),
            app.state.settings,
            app.state.password_service,
        )
        await service.create_admin(
            CreateAdminInput(
                email=email,
                display_name=display_name,
                password="Correct-Horse-42!",
                role=role,
            )
        )


@pytest.fixture
async def core_api(database_client: DatabaseClient, tmp_path: Path) -> AsyncIterator[CoreAPI]:
    settings = _settings(database_client, tmp_path / "media")
    repository_client = FakeRepositoryMetadataClient()
    app = create_app(
        settings,
        database_client=database_client,
        repository_metadata_client=repository_client,
    )
    await _create_admin(app, database_client)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        unauthorized = await client.get("/api/v1/admin/identity/profiles")
        assert unauthorized.status_code == 401
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "Correct-Horse-42!"},
        )
        assert login.status_code == 200, login.text
        csrf = login.json()["csrf_token"]
        yield CoreAPI(
            client=client,
            csrf=csrf,
            settings=settings,
            repository_client=repository_client,
        )


async def _create_profile(api: CoreAPI, *, name: str = "Yazeed Hasan") -> dict[str, Any]:
    response = await api.client.post(
        "/api/v1/admin/identity/profiles",
        headers=api.mutation_headers,
        json={
            "full_name": name,
            "headline": "AI and platform engineer",
            "short_bio": "I build production-grade software and AI systems.",
            "is_primary": True,
            "status": "published",
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


@pytest.mark.asyncio
async def test_public_composition_accepts_known_legacy_site_setting_keys(
    core_api: CoreAPI,
    database_client: DatabaseClient,
) -> None:
    legacy_configuration: dict[str, object] = {
        "site_name": "Upgraded portfolio",
        "default_title": "Upgraded portfolio title",
        "default_description": "Current presentation copy with legacy platform fields.",
        "locale": "en",
        "site_url": "https://legacy.example",
        "timezone": "UTC",
        "analytics_enabled": False,
    }
    async with database_client.session_factory() as session:
        session.add(
            FeatureSetting(
                key="site_settings",
                description="Persisted before presentation settings were typed.",
                enabled=True,
                configuration=legacy_configuration,
            )
        )
        await session.commit()

    for path in (
        "/api/v1/public/homepage",
        "/api/v1/public/site-shell",
        "/api/v1/public/site-presentation",
    ):
        response = await core_api.client.get(path)
        assert response.status_code == 200, response.text

    homepage = (await core_api.client.get("/api/v1/public/homepage")).json()
    assert homepage["site_presentation"]["site_name"] == "Upgraded portfolio"
    assert homepage["feature_configurations"]["site_settings"] == legacy_configuration


@pytest.mark.asyncio
async def test_homepage_composition_canonicalizes_a_persisted_retired_variant(
    core_api: CoreAPI,
    database_client: DatabaseClient,
) -> None:
    async with database_client.session_factory() as session:
        legacy_section = HomepageSection(
            section_type=HomepageSectionType.HERO,
            position=0,
            enabled=True,
            variant="editorial",
        )
        session.add(legacy_section)
        await session.commit()
        await session.refresh(legacy_section)
        legacy_section_id = legacy_section.id
        section_id = str(legacy_section_id)

    listed = await core_api.client.get("/api/v1/admin/content/sections?limit=100&offset=0")
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["variant"] == "portrait"

    saved = await core_api.client.put(
        "/api/v1/admin/content/sections/composition",
        headers=core_api.mutation_headers,
        json={
            "sections": [
                {
                    "id": section_id,
                    "section_type": "hero",
                    "position": 0,
                    "enabled": True,
                    "variant": "editorial",
                }
            ]
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()[0]["variant"] == "portrait"

    async with database_client.session_factory() as session:
        persisted = await session.get(HomepageSection, legacy_section_id)
        assert persisted is not None
        assert persisted.variant == "portrait"

    rejected = await core_api.client.post(
        "/api/v1/admin/content/sections",
        headers=core_api.mutation_headers,
        json={
            "section_type": "contact",
            "position": 1,
            "variant": "untrusted-client-variant",
        },
    )
    assert rejected.status_code == 422


@pytest.mark.asyncio
async def test_auth_is_deny_by_default_and_csrf_protects_mutations(
    core_api: CoreAPI,
) -> None:
    without_csrf = await core_api.client.post(
        "/api/v1/admin/identity/profiles",
        json={
            "full_name": "Blocked",
            "headline": "Blocked",
            "short_bio": "This mutation must be blocked without a CSRF token.",
        },
    )
    assert without_csrf.status_code == 403
    assert without_csrf.json()["error"]["code"] == "forbidden"

    me = await core_api.client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "owner"


@pytest.mark.asyncio
async def test_editor_can_author_drafts_but_sensitive_commands_are_owner_only(
    database_client: DatabaseClient,
    tmp_path: Path,
) -> None:
    settings = _settings(database_client, tmp_path / "media")
    app = create_app(settings, database_client=database_client)
    await _create_admin(app, database_client)
    await _create_admin(
        app,
        database_client,
        email="editor@example.com",
        display_name="Portfolio Editor",
        role=AdminRole.EDITOR,
    )

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as owner:
        login = await owner.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "Correct-Horse-42!"},
        )
        owner_headers = {settings.csrf_header_name: login.json()["csrf_token"]}
        profile = await owner.post(
            "/api/v1/admin/identity/profiles",
            headers=owner_headers,
            json={
                "full_name": "Owner-controlled identity",
                "headline": "Draft public identity",
                "short_bio": "Only the owner may change this identity lifecycle.",
                "is_primary": True,
            },
        )
        assert profile.status_code == 201, profile.text
        public_project = await owner.post(
            "/api/v1/admin/portfolio/projects",
            headers=owner_headers,
            json={
                "title": "Owner-published media parent",
                "slug": "owner-published-media-parent",
                "summary": "A public parent used to verify media publication permissions.",
                "status": "published",
            },
        )
        assert public_project.status_code == 201, public_project.text
        public_media = await owner.post(
            "/api/v1/admin/portfolio/project-media",
            headers=owner_headers,
            json={
                "project_id": public_project.json()["id"],
                "external_url": "https://cdn.example.com/owner-public.png",
                "media_type": "image/png",
                "alt_text": "Owner-controlled public project media",
                "is_visible": True,
            },
        )
        assert public_media.status_code == 201, public_media.text

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as editor:
        login = await editor.post(
            "/api/v1/auth/login",
            json={"email": "editor@example.com", "password": "Correct-Horse-42!"},
        )
        assert login.status_code == 200, login.text
        editor_headers = {settings.csrf_header_name: login.json()["csrf_token"]}

        draft = await editor.post(
            "/api/v1/admin/portfolio/categories",
            headers=editor_headers,
            json={
                "name": "Editor draft",
                "slug": "editor-draft",
                "description": "Editors may author draft taxonomy records.",
            },
        )
        assert draft.status_code == 201, draft.text
        edited = await editor.patch(
            f"/api/v1/admin/portfolio/categories/{draft.json()['id']}",
            headers=editor_headers,
            json={"description": "Editors may revise non-public draft content."},
        )
        assert edited.status_code == 200, edited.text

        metric = await editor.post(
            "/api/v1/admin/portfolio/metrics",
            headers=editor_headers,
            json={
                "subject_label": "Draft metric",
                "label": "Latency",
                "value": "Pending review",
                "context": "An editor-authored claim that is not approved.",
            },
        )
        assert metric.status_code == 201, metric.text

        forbidden_requests = [
            editor.post(
                "/api/v1/admin/portfolio/categories",
                headers=editor_headers,
                json={
                    "name": "Published by editor",
                    "slug": "published-by-editor",
                    "description": "This publication attempt must be denied.",
                    "status": "published",
                },
            ),
            editor.patch(
                f"/api/v1/admin/portfolio/categories/{draft.json()['id']}",
                headers=editor_headers,
                json={"is_visible": False},
            ),
            editor.put(
                f"/api/v1/admin/portfolio/categories/{draft.json()['id']}/status",
                headers=editor_headers,
                json={"status": "published"},
            ),
            editor.put(
                f"/api/v1/admin/portfolio/metrics/{metric.json()['id']}/approval",
                headers=editor_headers,
                json={},
            ),
            editor.put(
                "/api/v1/admin/content/features",
                headers=editor_headers,
                json={"key": "contact", "enabled": True},
            ),
            editor.put(
                "/api/v1/admin/content/sections/composition",
                headers=editor_headers,
                json={"sections": []},
            ),
            editor.put(
                f"/api/v1/admin/identity/profiles/{profile.json()['id']}/status",
                headers=editor_headers,
                json={"status": "published"},
            ),
            editor.put(
                "/api/v1/admin/portfolio/projects/featured-order",
                headers=editor_headers,
                json={"project_ids": []},
            ),
            editor.patch(
                f"/api/v1/admin/portfolio/project-media/{public_media.json()['id']}",
                headers=editor_headers,
                json={"is_visible": False},
            ),
            editor.delete(
                f"/api/v1/admin/portfolio/project-media/{public_media.json()['id']}",
                headers=editor_headers,
            ),
            editor.post(
                "/api/v1/admin/engagement/sponsorship",
                headers=editor_headers,
                json={
                    "slug": "editor-destination",
                    "title": "Editor destination",
                    "description": "Sensitive external destination.",
                    "kind": "external",
                    "cta_label": "Open",
                    "destination_url": "https://github.com/sponsors/sensitive",
                },
            ),
            editor.post(
                "/api/v1/admin/engagement/contact-submissions/missing/retry-notification",
                headers=editor_headers,
            ),
            editor.post(
                "/api/v1/admin/engagement/contact-notifications/process-due",
                headers=editor_headers,
            ),
        ]
        responses = await asyncio.gather(*forbidden_requests)
        assert [response.status_code for response in responses] == [403] * len(responses)
        assert all(response.json()["error"]["code"] == "forbidden" for response in responses)


@pytest.mark.asyncio
async def test_engagement_admin_routes_are_authenticated_and_csrf_protected(
    core_api: CoreAPI,
) -> None:
    inbox = await core_api.client.get("/api/v1/admin/engagement/contact-submissions")
    assert inbox.status_code == 200
    assert inbox.json()["total"] == 0
    blocked_drain = await core_api.client.post(
        "/api/v1/admin/engagement/contact-notifications/process-due"
    )
    assert blocked_drain.status_code == 403
    drained = await core_api.client.post(
        "/api/v1/admin/engagement/contact-notifications/process-due",
        headers=core_api.mutation_headers,
    )
    assert drained.status_code == 200
    assert drained.json() == {
        "selected_count": 0,
        "sent_count": 0,
        "not_sent_by_this_worker_count": 0,
    }

    payload = {
        "slug": "test-sponsor",
        "title": "Test sponsorship",
        "description": "An integration-only sponsorship option.",
        "kind": "external",
        "cta_label": "Sponsor",
        "destination_url": "https://github.com/sponsors/example",
        "is_published": True,
    }
    blocked = await core_api.client.post(
        "/api/v1/admin/engagement/sponsorship",
        json=payload,
    )
    assert blocked.status_code == 403

    created = await core_api.client.post(
        "/api/v1/admin/engagement/sponsorship",
        headers=core_api.mutation_headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    listing = await core_api.client.get("/api/v1/admin/engagement/sponsorship")
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["slug"] == "test-sponsor"
    assert (await core_api.client.get("/api/v1/sponsorship")).json()["items"] == []

    archived = await core_api.client.delete(
        f"/api/v1/admin/engagement/sponsorship/{created.json()['id']}",
        headers=core_api.mutation_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True


@pytest.mark.asyncio
async def test_profile_and_resume_replacement_keep_stable_public_contract(
    core_api: CoreAPI,
    database_client: DatabaseClient,
) -> None:
    profile = await _create_profile(core_api)
    public_profile = await core_api.client.get("/api/v1/public/profile")
    assert public_profile.status_code == 200
    assert public_profile.json()["id"] == profile["id"]

    first_pdf = b"%PDF-1.7\nfirst version\n%%EOF"
    first_upload = await core_api.client.post(
        "/api/v1/admin/identity/resume-versions",
        headers=core_api.mutation_headers,
        data={
            "profile_id": profile["id"],
            "version_label": "2026 v1",
            "download_name": "Yazeed-Hasan-Resume.pdf",
        },
        files={"file": ("resume-v1.pdf", first_pdf, "application/pdf")},
    )
    assert first_upload.status_code == 201, first_upload.text
    publish_first = await core_api.client.put(
        f"/api/v1/admin/identity/resume-versions/{first_upload.json()['id']}/publish-current",
        headers=core_api.mutation_headers,
    )
    assert publish_first.status_code == 200
    first_download = await core_api.client.get("/api/v1/public/resume")
    assert first_download.status_code == 200
    assert first_download.content == first_pdf

    second_pdf = b"%PDF-1.7\nsecond version\n%%EOF"
    second_upload = await core_api.client.post(
        "/api/v1/admin/identity/resume-versions",
        headers=core_api.mutation_headers,
        data={
            "profile_id": profile["id"],
            "version_label": "2026 v2",
            "download_name": "Yazeed-Hasan-Resume.pdf",
        },
        files={"file": ("resume-v2.pdf", second_pdf, "application/pdf")},
    )
    assert second_upload.status_code == 201
    publish_second = await core_api.client.put(
        f"/api/v1/admin/identity/resume-versions/{second_upload.json()['id']}/publish-current",
        headers=core_api.mutation_headers,
    )
    assert publish_second.status_code == 200

    replacement = await core_api.client.get("/api/v1/public/resume")
    assert replacement.status_code == 200
    assert replacement.content == second_pdf
    assert replacement.request.url.path == first_download.request.url.path

    cannot_archive_current = await core_api.client.delete(
        f"/api/v1/admin/identity/resume-versions/{second_upload.json()['id']}",
        headers=core_api.mutation_headers,
    )
    assert cannot_archive_current.status_code == 409
    async with database_client.session_factory() as session:
        current_count = await session.scalar(
            select(func.count(ResumeVersion.id)).where(ResumeVersion.is_current.is_(True))
        )
    assert current_count == 1


@pytest.mark.asyncio
async def test_publication_approval_feature_gates_and_featured_limit(
    core_api: CoreAPI,
) -> None:
    feature = await core_api.client.put(
        "/api/v1/admin/content/features",
        headers=core_api.mutation_headers,
        json={"key": "work.enabled", "enabled": False},
    )
    assert feature.status_code == 200
    section = await core_api.client.post(
        "/api/v1/admin/content/sections",
        headers=core_api.mutation_headers,
        json={
            "section_type": "selected_work",
            "position": 1,
            "feature_key": "work.enabled",
            "status": "published",
        },
    )
    assert section.status_code == 201, section.text

    project_ids: list[str] = []
    for rank in range(1, 5):
        project = await core_api.client.post(
            "/api/v1/admin/portfolio/projects",
            headers=core_api.mutation_headers,
            json={
                "title": f"Project {rank}",
                "slug": f"project-{rank}",
                "summary": f"Evidence-backed project {rank}.",
                "featured_rank": rank,
                "status": "published",
            },
        )
        assert project.status_code == 201, project.text
        project_ids.append(project.json()["id"])

    hidden_homepage = await core_api.client.get("/api/v1/public/homepage")
    assert hidden_homepage.status_code == 200
    assert hidden_homepage.json()["sections"] == []

    enabled = await core_api.client.put(
        "/api/v1/admin/content/features",
        headers=core_api.mutation_headers,
        json={"key": "work.enabled", "enabled": True},
    )
    assert enabled.status_code == 200
    homepage = await core_api.client.get("/api/v1/public/homepage")
    assert len(homepage.json()["sections"]) == 1
    assert len(homepage.json()["sections"][0]["data"]) == 3

    invalid_metric = await core_api.client.post(
        "/api/v1/admin/portfolio/metrics",
        headers=core_api.mutation_headers,
        json={"label": "Throughput", "value": "2x", "context": "Measured result."},
    )
    assert invalid_metric.status_code == 422

    metric = await core_api.client.post(
        "/api/v1/admin/portfolio/metrics",
        headers=core_api.mutation_headers,
        json={
            "project_id": project_ids[0],
            "label": "Throughput",
            "value": "2x",
            "context": "Measured against the approved baseline.",
            "evidence": {
                "kind": "document_reference",
                "visibility": "private_review",
                "reference_text": "Internal benchmark report 2026-08",
                "provenance": "Owner-reviewed benchmark archive",
                "captured_at": "2026-08-01",
            },
            "status": "published",
        },
    )
    assert metric.status_code == 201
    assert metric.json()["is_approved"] is False
    assert (await core_api.client.get("/api/v1/public/metrics")).json() == []

    approved = await core_api.client.put(
        f"/api/v1/admin/portfolio/metrics/{metric.json()['id']}/approval",
        headers=core_api.mutation_headers,
    )
    assert approved.status_code == 200
    assert len((await core_api.client.get("/api/v1/public/metrics")).json()) == 1

    material_edit = await core_api.client.patch(
        f"/api/v1/admin/portfolio/metrics/{metric.json()['id']}",
        headers=core_api.mutation_headers,
        json={"label": "Updated throughput"},
    )
    assert material_edit.status_code == 200
    assert material_edit.json()["is_approved"] is False
    assert (await core_api.client.get("/api/v1/public/metrics")).json() == []

    secret_configuration = await core_api.client.post(
        "/api/v1/admin/content/sections",
        headers=core_api.mutation_headers,
        json={
            "section_type": "editorial",
            "position": 2,
            "configuration": {"api_key": "must-not-be-published"},
        },
    )
    assert secret_configuration.status_code == 422


@pytest.mark.asyncio
async def test_public_projection_enforces_every_parent_state_and_hides_approval_audit(
    core_api: CoreAPI,
) -> None:
    category = await core_api.client.post(
        "/api/v1/admin/portfolio/categories",
        headers=core_api.mutation_headers,
        json={
            "name": "Private taxonomy",
            "slug": "private-taxonomy",
            "description": "A category whose ancestry controls its public child.",
            "status": "draft",
        },
    )
    assert category.status_code == 201, category.text
    skill = await core_api.client.post(
        "/api/v1/admin/portfolio/skills",
        headers=core_api.mutation_headers,
        json={
            "category_id": category.json()["id"],
            "name": "Ancestry-safe skill",
            "slug": "ancestry-safe-skill",
            "status": "published",
        },
    )
    assert skill.status_code == 201, skill.text
    draft_category_skill = (await core_api.client.get("/api/v1/public/skills")).json()[0]
    assert draft_category_skill["category"] is None
    assert "category_id" not in draft_category_skill
    assert "status" not in draft_category_skill

    category_id = category.json()["id"]
    category_status = f"/api/v1/admin/portfolio/categories/{category_id}/status"
    assert (
        await core_api.client.put(
            category_status,
            headers=core_api.mutation_headers,
            json={"status": "published"},
        )
    ).status_code == 200
    assert (await core_api.client.get("/api/v1/public/skills")).json()[0]["category"][
        "id"
    ] == category_id

    for status_value in ("draft", "hidden", "archived"):
        changed = await core_api.client.put(
            category_status,
            headers=core_api.mutation_headers,
            json={"status": status_value},
        )
        assert changed.status_code == 200, changed.text
        assert (await core_api.client.get("/api/v1/public/skills")).json()[0]["category"] is None
        assert (
            await core_api.client.put(
                category_status,
                headers=core_api.mutation_headers,
                json={"status": "published"},
            )
        ).status_code == 200
    assert (
        await core_api.client.patch(
            f"/api/v1/admin/portfolio/categories/{category_id}",
            headers=core_api.mutation_headers,
            json={"noindex": True},
        )
    ).status_code == 200
    assert (await core_api.client.get("/api/v1/public/skills")).json()[0]["category"] is None
    assert (
        await core_api.client.patch(
            f"/api/v1/admin/portfolio/categories/{category_id}",
            headers=core_api.mutation_headers,
            json={"noindex": False},
        )
    ).status_code == 200

    project = await core_api.client.post(
        "/api/v1/admin/portfolio/projects",
        headers=core_api.mutation_headers,
        json={
            "title": "Compositional publication",
            "slug": "compositional-publication",
            "summary": "Every populated evidence parent must remain public.",
            "status": "published",
        },
    )
    experience = await core_api.client.post(
        "/api/v1/admin/portfolio/experiences",
        headers=core_api.mutation_headers,
        json={
            "organization": "Publication Authority",
            "role": "Reviewer",
            "start_date": "2025-01-01",
            "summary": "A second independent publication parent.",
            "status": "published",
        },
    )
    assert project.status_code == experience.status_code == 201
    metric = await core_api.client.post(
        "/api/v1/admin/portfolio/metrics",
        headers=core_api.mutation_headers,
        json={
            "project_id": project.json()["id"],
            "experience_id": experience.json()["id"],
            "label": "Publication coverage",
            "value": "100%",
            "context": "Both populated parents passed independent publication checks.",
            "evidence": {
                "kind": "public_url",
                "visibility": "public",
                "reference_url": "https://evidence.example/publication-matrix",
                "public_label": "Reviewed publication matrix",
                "provenance": "Owner-controlled verification record",
                "captured_at": "2026-08-28",
            },
            "status": "published",
        },
    )
    assert metric.status_code == 201, metric.text
    approved = await core_api.client.put(
        f"/api/v1/admin/portfolio/metrics/{metric.json()['id']}/approval",
        headers=core_api.mutation_headers,
    )
    assert approved.status_code == 200, approved.text

    public_metric = (await core_api.client.get("/api/v1/public/metrics")).json()[0]
    assert public_metric["public_evidence"] == {
        "label": "Reviewed publication matrix",
        "url": "https://evidence.example/publication-matrix",
        "captured_at": "2026-08-28",
    }
    assert {
        "is_approved",
        "approved_at",
        "approved_by_admin_id",
        "approved_revision_hash",
        "created_by_admin_id",
        "evidence",
    }.isdisjoint(public_metric)

    feature = await core_api.client.put(
        "/api/v1/admin/content/features",
        headers=core_api.mutation_headers,
        json={"key": "metrics", "enabled": True},
    )
    section = await core_api.client.post(
        "/api/v1/admin/content/sections",
        headers=core_api.mutation_headers,
        json={
            "section_type": "metrics",
            "position": 1,
            "feature_key": "metrics",
            "status": "published",
        },
    )
    assert feature.status_code == 200 and section.status_code == 201

    async def assert_metric_visibility(expected: bool) -> None:
        direct = (await core_api.client.get("/api/v1/public/metrics")).json()
        assert bool(direct) is expected
        detail = await core_api.client.get("/api/v1/public/projects/compositional-publication")
        if detail.status_code == 200:
            assert bool(detail.json()["metrics"]) is expected
        homepage = (await core_api.client.get("/api/v1/public/homepage")).json()
        metric_section = next(
            item for item in homepage["sections"] if item["section"]["section_type"] == "metrics"
        )
        assert bool(metric_section["data"]) is expected

    await assert_metric_visibility(True)
    for resource, entity_id in (
        ("projects", project.json()["id"]),
        ("experiences", experience.json()["id"]),
    ):
        endpoint = f"/api/v1/admin/portfolio/{resource}/{entity_id}"
        for status_value in ("draft", "hidden", "archived"):
            changed = await core_api.client.put(
                f"{endpoint}/status",
                headers=core_api.mutation_headers,
                json={"status": status_value},
            )
            assert changed.status_code == 200, changed.text
            await assert_metric_visibility(False)
            restored = await core_api.client.put(
                f"{endpoint}/status",
                headers=core_api.mutation_headers,
                json={"status": "published"},
            )
            assert restored.status_code == 200, restored.text
            await assert_metric_visibility(True)
        hidden_from_index = await core_api.client.patch(
            endpoint,
            headers=core_api.mutation_headers,
            json={"noindex": True},
        )
        assert hidden_from_index.status_code == 200, hidden_from_index.text
        await assert_metric_visibility(False)
        restored_index = await core_api.client.patch(
            endpoint,
            headers=core_api.mutation_headers,
            json={"noindex": False},
        )
        assert restored_index.status_code == 200, restored_index.text
        await assert_metric_visibility(True)


@pytest.mark.asyncio
async def test_public_resume_is_bound_to_the_exact_selected_profile(core_api: CoreAPI) -> None:
    first = await _create_profile(core_api, name="First Public Identity")
    first_upload = await core_api.client.post(
        "/api/v1/admin/identity/resume-versions",
        headers=core_api.mutation_headers,
        data={
            "profile_id": first["id"],
            "version_label": "First profile resume",
            "download_name": "first-profile.pdf",
        },
        files={"file": ("first.pdf", b"%PDF-1.7\nfirst\n%%EOF", "application/pdf")},
    )
    assert first_upload.status_code == 201, first_upload.text
    assert (
        await core_api.client.put(
            f"/api/v1/admin/identity/resume-versions/{first_upload.json()['id']}/publish-current",
            headers=core_api.mutation_headers,
        )
    ).status_code == 200

    second = await _create_profile(core_api, name="Selected Public Identity")
    public_profile = await core_api.client.get("/api/v1/public/profile")
    assert public_profile.json()["id"] == second["id"]
    assert (await core_api.client.get("/api/v1/public/resume/meta")).status_code == 404

    second_upload = await core_api.client.post(
        "/api/v1/admin/identity/resume-versions",
        headers=core_api.mutation_headers,
        data={
            "profile_id": second["id"],
            "version_label": "Selected profile resume",
            "download_name": "selected-profile.pdf",
        },
        files={"file": ("selected.pdf", b"%PDF-1.7\nselected\n%%EOF", "application/pdf")},
    )
    assert second_upload.status_code == 201, second_upload.text
    assert (
        await core_api.client.put(
            f"/api/v1/admin/identity/resume-versions/{second_upload.json()['id']}/publish-current",
            headers=core_api.mutation_headers,
        )
    ).status_code == 200
    public_resume = (await core_api.client.get("/api/v1/public/resume/meta")).json()
    assert public_resume["version_label"] == "Selected profile resume"
    assert {"profile_id", "storage_key"}.isdisjoint(public_resume)


@pytest.mark.asyncio
async def test_structured_evidence_rejects_invalid_sources_and_revokes_archived_media(
    core_api: CoreAPI,
) -> None:
    project = await core_api.client.post(
        "/api/v1/admin/portfolio/projects",
        headers=core_api.mutation_headers,
        json={
            "title": "Evidence lifecycle",
            "slug": "evidence-lifecycle",
            "summary": "Managed evidence remains immutable and review-bound.",
            "status": "published",
        },
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]
    base = {
        "project_id": project_id,
        "label": "Evidence quality",
        "value": "1",
        "context": "The evidence gate rejects weak or inaccessible sources.",
        "status": "published",
    }
    invalid_evidence = [
        {
            "kind": "document_reference",
            "reference_text": "x",
            "provenance": "Owner archive",
            "captured_at": "2026-08-28",
        },
        {
            "kind": "public_url",
            "reference_url": "http://evidence.example/insecure",
            "provenance": "Owner archive",
            "captured_at": "2026-08-28",
        },
        {
            "kind": "public_url",
            "reference_url": "https://evidence.example/one",
            "reference_text": "Second conflicting locator",
            "provenance": "Owner archive",
            "captured_at": "2026-08-28",
        },
        {
            "kind": "managed_media",
            "managed_media_id": "00000000-0000-0000-0000-000000000099",
            "provenance": "Owner archive",
            "captured_at": "2026-08-28",
        },
    ]
    for index, evidence in enumerate(invalid_evidence):
        rejected = await core_api.client.post(
            "/api/v1/admin/portfolio/metrics",
            headers=core_api.mutation_headers,
            json={**base, "label": f"Rejected evidence {index}", "evidence": evidence},
        )
        assert rejected.status_code == 422, rejected.text

    external = await core_api.client.post(
        "/api/v1/admin/portfolio/project-media",
        headers=core_api.mutation_headers,
        json={
            "project_id": project_id,
            "external_url": "https://cdn.example.com/not-managed.pdf",
            "media_type": "application/pdf",
            "alt_text": "External evidence",
        },
    )
    assert external.status_code == 201
    external_rejected = await core_api.client.post(
        "/api/v1/admin/portfolio/metrics",
        headers=core_api.mutation_headers,
        json={
            **base,
            "label": "External is not managed",
            "evidence": {
                "kind": "managed_media",
                "managed_media_id": external.json()["id"],
                "provenance": "External asset reference",
                "captured_at": "2026-08-28",
            },
        },
    )
    assert external_rejected.status_code == 422

    uploaded = await core_api.client.post(
        "/api/v1/admin/portfolio/project-media/upload",
        headers=core_api.mutation_headers,
        data={
            "project_id": project_id,
            "alt_text": "Reviewed evidence document",
            "caption": "Immutable managed source",
        },
        files={"file": ("review.pdf", b"%PDF-1.7\nreviewed\n%%EOF", "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    lookup = await core_api.client.get("/api/v1/admin/portfolio/project-media?search=review")
    assert lookup.status_code == 200
    assert [item["id"] for item in lookup.json()["items"]] == [uploaded.json()["id"]]

    missing_upload = await core_api.client.post(
        "/api/v1/admin/portfolio/project-media/upload",
        headers=core_api.mutation_headers,
        data={"project_id": project_id, "alt_text": "Missing managed source"},
        files={"file": ("missing.pdf", b"%PDF-1.7\nmissing\n%%EOF", "application/pdf")},
    )
    assert missing_upload.status_code == 201, missing_upload.text
    missing_path = (
        core_api.settings.storage_root
        / "projects"
        / project_id
        / f"{missing_upload.json()['id']}.pdf"
    )
    assert missing_path.is_file()
    missing_path.unlink()
    missing_rejected = await core_api.client.post(
        "/api/v1/admin/portfolio/metrics",
        headers=core_api.mutation_headers,
        json={
            **base,
            "label": "Missing managed source",
            "evidence": {
                "kind": "managed_media",
                "managed_media_id": missing_upload.json()["id"],
                "provenance": "Deleted test-only managed artifact",
                "captured_at": "2026-08-28",
            },
        },
    )
    assert missing_rejected.status_code == 422

    managed_metric = await core_api.client.post(
        "/api/v1/admin/portfolio/metrics",
        headers=core_api.mutation_headers,
        json={
            **base,
            "label": "Managed evidence",
            "evidence": {
                "kind": "managed_media",
                "visibility": "public",
                "managed_media_id": uploaded.json()["id"],
                "public_label": "Reviewed evidence document",
                "provenance": "Owner-uploaded immutable artifact",
                "captured_at": "2026-08-28",
            },
        },
    )
    assert managed_metric.status_code == 201, managed_metric.text
    approved = await core_api.client.put(
        f"/api/v1/admin/portfolio/metrics/{managed_metric.json()['id']}/approval",
        headers=core_api.mutation_headers,
    )
    assert approved.status_code == 200, approved.text
    projected = (await core_api.client.get("/api/v1/public/metrics")).json()[0]
    assert projected["public_evidence"]["url"] == (
        f"/api/v1/public/project-media/{uploaded.json()['id']}"
    )

    archived = await core_api.client.delete(
        f"/api/v1/admin/portfolio/project-media/{uploaded.json()['id']}",
        headers=core_api.mutation_headers,
    )
    assert archived.status_code == 200
    assert (await core_api.client.get("/api/v1/public/metrics")).json() == []
    admin_metrics = (await core_api.client.get("/api/v1/admin/portfolio/metrics")).json()["items"]
    managed_admin = next(
        item for item in admin_metrics if item["id"] == managed_metric.json()["id"]
    )
    assert managed_admin["is_approved"] is False
    assert managed_admin["evidence"]["archived_at"] is not None

    private_metric = await core_api.client.post(
        "/api/v1/admin/portfolio/metrics",
        headers=core_api.mutation_headers,
        json={
            **base,
            "label": "Private review evidence",
            "evidence": {
                "kind": "document_reference",
                "visibility": "private_review",
                "reference_text": "Controlled report revision 42, page 7",
                "provenance": "Private owner-controlled report",
                "captured_at": "2026-08-28",
                "reviewer_note": "Never expose this note publicly.",
            },
        },
    )
    assert private_metric.status_code == 201, private_metric.text
    assert (
        await core_api.client.put(
            f"/api/v1/admin/portfolio/metrics/{private_metric.json()['id']}/approval",
            headers=core_api.mutation_headers,
        )
    ).status_code == 200
    private_public = (await core_api.client.get("/api/v1/public/metrics")).json()[0]
    assert private_public["public_evidence"] is None
    assert "reviewer_note" not in private_public


@pytest.mark.asyncio
async def test_archived_features_fail_closed_across_every_public_consumer_and_restore(
    database_client: DatabaseClient,
    tmp_path: Path,
) -> None:
    settings = _settings(
        database_client,
        tmp_path / "feature-state-media",
        contact_enabled=True,
        sponsorship_enabled=True,
        assistant_enabled=True,
        ai_provider_api_key="test-only-ai-provider-key",
        ai_model="test-model",
        email_enabled=True,
        smtp_host="smtp.test.invalid",
        email_from_address="portfolio@example.com",
        contact_notification_to="owner@example.com",
    )
    email_client = SuccessfulEmailClient()
    app = create_app(
        settings,
        database_client=database_client,
        email_client=email_client,
        ai_provider_client=AvailableAIClient(),
        repository_metadata_client=FakeRepositoryMetadataClient(),
    )
    await _create_admin(app, database_client)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "Correct-Horse-42!"},
        )
        assert login.status_code == 200
        mutation_headers = {settings.csrf_header_name: login.json()["csrf_token"]}
        profile = await client.post(
            "/api/v1/admin/identity/profiles",
            headers=mutation_headers,
            json={
                "full_name": "Feature State Owner",
                "headline": "Canonical feature-state verification",
                "short_bio": "Archived capabilities must remain unavailable everywhere.",
                "is_primary": True,
                "status": "published",
            },
        )
        assert profile.status_code == 201, profile.text

        features: dict[str, str] = {}
        for key in ("contact", "sponsorship", "assistant"):
            response = await client.put(
                "/api/v1/admin/content/features",
                headers=mutation_headers,
                json={"key": key, "enabled": True},
            )
            assert response.status_code == 200, response.text
            features[key] = response.json()["id"]
            section = await client.post(
                "/api/v1/admin/content/sections",
                headers=mutation_headers,
                json={
                    "section_type": key,
                    "position": len(features),
                    "feature_key": key,
                    "status": "published",
                },
            )
            assert section.status_code == 201, section.text

        sponsorship = await client.post(
            "/api/v1/admin/engagement/sponsorship",
            headers=mutation_headers,
            json={
                "slug": "feature-state-sponsor",
                "title": "Feature-state sponsorship",
                "description": "A canonical sponsorship record used by the lifecycle matrix.",
                "kind": "external",
                "cta_label": "Sponsor",
                "destination_url": "https://github.com/sponsors/example",
                "is_published": True,
            },
        )
        assert sponsorship.status_code == 201, sponsorship.text

        contact_payload = {
            "name": "Feature State Tester",
            "email": "feature-state@example.com",
            "category": "general",
            "subject": "Feature lifecycle",
            "message": "This sufficiently long message proves the enabled public workflow.",
            "consent": True,
            "website": "",
        }
        enabled_contact = await client.post(
            "/api/v1/contact",
            headers={
                **mutation_headers,
                "Idempotency-Key": "feature-state-enabled-0001",
            },
            json=contact_payload,
        )
        assert enabled_contact.status_code == 202, enabled_contact.text
        assert len(email_client.notifications) == 1
        assert (await client.get("/api/v1/contact/options")).json()["accepting_messages"] is True
        assert len((await client.get("/api/v1/sponsorship")).json()["items"]) == 1
        enabled_shell = (await client.get("/api/v1/public/site-shell")).json()
        assert all(enabled_shell["features"][key] is True for key in features)
        enabled_home = (await client.get("/api/v1/public/homepage")).json()
        assert {item["section"]["section_type"] for item in enabled_home["sections"]} == set(
            features
        )
        enabled_sitemap = {
            item["url"] for item in (await client.get("/api/v1/discovery/sitemap")).json()
        }
        assert {
            "https://portfolio.example/contact",
            "https://portfolio.example/sponsor",
        }.issubset(enabled_sitemap)

        for key, feature_id in features.items():
            archived = await client.delete(
                f"/api/v1/admin/content/features/{feature_id}",
                headers=mutation_headers,
            )
            assert archived.status_code == 200, f"{key}: {archived.text}"
            assert archived.json()["archived_at"] is not None

        disabled_shell = (await client.get("/api/v1/public/site-shell")).json()
        assert all(disabled_shell["features"][key] is False for key in features)
        assert (await client.get("/api/v1/contact/options")).json()["accepting_messages"] is False
        rejected_contact = await client.post(
            "/api/v1/contact",
            headers={
                **mutation_headers,
                "Idempotency-Key": "feature-state-disabled-0001",
            },
            json={**contact_payload, "message": "This request must fail while archived."},
        )
        assert rejected_contact.status_code == 503
        assert len(email_client.notifications) == 1
        assert (await client.get("/api/v1/sponsorship")).json()["items"] == []
        rejected_assistant = await client.post(
            "/api/v1/assistant/query",
            headers=mutation_headers,
            json={"question": "Which published evidence is available?"},
        )
        assert rejected_assistant.status_code == 503
        assert (await client.get("/api/v1/public/homepage")).json()["sections"] == []
        disabled_sitemap = {
            item["url"] for item in (await client.get("/api/v1/discovery/sitemap")).json()
        }
        assert "https://portfolio.example/contact" not in disabled_sitemap
        assert "https://portfolio.example/sponsor" not in disabled_sitemap

        for key in features:
            explicitly_disabled = await client.put(
                "/api/v1/admin/content/features",
                headers=mutation_headers,
                json={"key": key, "enabled": False},
            )
            assert explicitly_disabled.status_code == 200
            assert explicitly_disabled.json()["archived_at"] is None
        still_disabled = (await client.get("/api/v1/public/site-shell")).json()
        assert all(still_disabled["features"][key] is False for key in features)

        for key in features:
            restored = await client.put(
                "/api/v1/admin/content/features",
                headers=mutation_headers,
                json={"key": key, "enabled": True},
            )
            assert restored.status_code == 200
        restored_shell = (await client.get("/api/v1/public/site-shell")).json()
        assert all(restored_shell["features"][key] is True for key in features)
        restored_home = (await client.get("/api/v1/public/homepage")).json()
        assert {item["section"]["section_type"] for item in restored_home["sections"]} == set(
            features
        )
        restored_contact = await client.post(
            "/api/v1/contact",
            headers={
                **mutation_headers,
                "Idempotency-Key": "feature-state-restored-0001",
            },
            json={**contact_payload, "message": "This request succeeds after explicit restore."},
        )
        assert restored_contact.status_code == 202, restored_contact.text
        assert len(email_client.notifications) == 2


@pytest.mark.asyncio
async def test_skill_project_counts_use_the_complete_public_project_set(
    core_api: CoreAPI,
) -> None:
    counted_skill = await core_api.client.post(
        "/api/v1/admin/portfolio/skills",
        headers=core_api.mutation_headers,
        json={"name": "Counted skill", "slug": "counted-skill", "status": "published"},
    )
    zero_skill = await core_api.client.post(
        "/api/v1/admin/portfolio/skills",
        headers=core_api.mutation_headers,
        json={"name": "Zero skill", "slug": "zero-skill", "status": "published"},
    )
    assert counted_skill.status_code == zero_skill.status_code == 201
    skill_id = counted_skill.json()["id"]

    projects: dict[str, dict[str, Any]] = {}
    cases = (
        ("public-unfeatured", "published", False),
        ("public-noindex", "published", True),
        ("draft-project", "draft", False),
        ("hidden-project", "hidden", False),
        ("archived-project", "archived", False),
    )
    for slug, status_value, noindex in cases:
        response = await core_api.client.post(
            "/api/v1/admin/portfolio/projects",
            headers=core_api.mutation_headers,
            json={
                "title": slug.replace("-", " ").title(),
                "slug": slug,
                "summary": f"Lifecycle count fixture for {slug}.",
                "skill_ids": [skill_id],
                "noindex": noindex,
                "status": status_value,
            },
        )
        assert response.status_code == 201, response.text
        projects[slug] = response.json()

    public_skills = (await core_api.client.get("/api/v1/public/skills")).json()
    by_slug = {item["slug"]: item for item in public_skills}
    # noindex is an indexing policy, not an access policy, so it remains valid
    # evidence in the public UI. Featured rank is intentionally irrelevant.
    assert by_slug["counted-skill"]["project_count"] == 2
    assert by_slug["zero-skill"]["project_count"] == 0

    published_draft = await core_api.client.put(
        f"/api/v1/admin/portfolio/projects/{projects['draft-project']['id']}/status",
        headers=core_api.mutation_headers,
        json={"status": "published"},
    )
    assert published_draft.status_code == 200
    assert (
        next(
            item
            for item in (await core_api.client.get("/api/v1/public/skills")).json()
            if item["id"] == skill_id
        )["project_count"]
        == 3
    )

    archived_public = await core_api.client.put(
        f"/api/v1/admin/portfolio/projects/{projects['public-unfeatured']['id']}/status",
        headers=core_api.mutation_headers,
        json={"status": "archived"},
    )
    assert archived_public.status_code == 200
    assert (
        next(
            item
            for item in (await core_api.client.get("/api/v1/public/skills")).json()
            if item["id"] == skill_id
        )["project_count"]
        == 2
    )


@pytest.mark.asyncio
async def test_related_project_and_article_contracts_cover_empty_single_and_multiple(
    core_api: CoreAPI,
) -> None:
    category = await core_api.client.post(
        "/api/v1/admin/portfolio/categories",
        headers=core_api.mutation_headers,
        json={
            "name": "Related systems",
            "slug": "related-systems",
            "description": "Deterministic related-content grouping.",
            "status": "published",
        },
    )
    single_category = await core_api.client.post(
        "/api/v1/admin/portfolio/categories",
        headers=core_api.mutation_headers,
        json={
            "name": "Single relation",
            "slug": "single-relation",
            "description": "Exactly one related record.",
            "status": "published",
        },
    )
    assert category.status_code == single_category.status_code == 201

    async def create_project(
        slug: str,
        *,
        category_id: str | None,
        status_value: str = "published",
        noindex: bool = False,
    ) -> dict[str, Any]:
        response = await core_api.client.post(
            "/api/v1/admin/portfolio/projects",
            headers=core_api.mutation_headers,
            json={
                "category_id": category_id,
                "title": slug.replace("-", " ").title(),
                "slug": slug,
                "summary": f"Related-content fixture {slug}.",
                "status": status_value,
                "noindex": noindex,
            },
        )
        assert response.status_code == 201, response.text
        return cast(dict[str, Any], response.json())

    await create_project("related-current", category_id=category.json()["id"])
    expected_related = {
        (await create_project(f"related-{index}", category_id=category.json()["id"]))["id"]
        for index in range(3)
    }
    await create_project("related-noindex", category_id=category.json()["id"], noindex=True)
    await create_project("related-draft", category_id=category.json()["id"], status_value="draft")
    multiple = await core_api.client.get("/api/v1/public/projects/related-current")
    assert multiple.status_code == 200
    assert {item["id"] for item in multiple.json()["related_projects"]} == expected_related

    await create_project("single-current", category_id=single_category.json()["id"])
    single_candidate = await create_project(
        "single-candidate", category_id=single_category.json()["id"]
    )
    single = await core_api.client.get("/api/v1/public/projects/single-current")
    assert [item["id"] for item in single.json()["related_projects"]] == [single_candidate["id"]]
    await create_project("unrelated-current", category_id=None)
    assert (await core_api.client.get("/api/v1/public/projects/unrelated-current")).json()[
        "related_projects"
    ] == []

    async def create_article(
        slug: str,
        *,
        topics: list[str],
        status_value: str = "published",
        noindex: bool = False,
    ) -> dict[str, Any]:
        response = await core_api.client.post(
            "/api/v1/admin/content/articles",
            headers=core_api.mutation_headers,
            json={
                "title": slug.replace("-", " ").title(),
                "slug": slug,
                "excerpt": f"Related writing fixture {slug}.",
                "body_markdown": f"# {slug}\n\nCanonical related writing content.",
                "topics": topics,
                "status": status_value,
                "noindex": noindex,
            },
        )
        assert response.status_code == 201, response.text
        return cast(dict[str, Any], response.json())

    await create_article("article-current", topics=["shared"])
    article_candidates = {
        (await create_article(f"article-related-{index}", topics=["shared"]))["id"]
        for index in range(2)
    }
    await create_article("article-noindex", topics=["shared"], noindex=True)
    await create_article("article-draft", topics=["shared"], status_value="draft")
    await create_article("article-unrelated", topics=["other"])
    article_detail = await core_api.client.get("/api/v1/public/articles/article-current")
    assert article_detail.status_code == 200
    assert {item["id"] for item in article_detail.json()["related_articles"]} == article_candidates
    await create_article("article-empty", topics=["unique"])
    assert (await core_api.client.get("/api/v1/public/articles/article-empty")).json()[
        "related_articles"
    ] == []


@pytest.mark.asyncio
async def test_featured_slots_follow_active_public_lifecycle_and_swap_atomically(
    core_api: CoreAPI,
) -> None:
    async def create_project(
        slug: str,
        *,
        rank: int | None,
        status: str = "published",
    ) -> dict[str, Any]:
        response = await core_api.client.post(
            "/api/v1/admin/portfolio/projects",
            headers=core_api.mutation_headers,
            json={
                "title": slug.replace("-", " ").title(),
                "slug": slug,
                "summary": f"Editorial summary for {slug}.",
                "featured_rank": rank,
                "status": status,
            },
        )
        assert response.status_code == 201, response.text
        return cast(dict[str, Any], response.json())

    draft = await create_project("draft-intent", rank=1, status="draft")
    first = await create_project("active-first", rank=1)
    second = await create_project("active-second", rank=2)

    occupied = await core_api.client.get("/api/v1/admin/portfolio/projects/featured-order")
    assert occupied.status_code == 200, occupied.text
    assert occupied.json()["limit"] == 3
    assert [item["id"] for item in occupied.json()["projects"]] == [
        first["id"],
        second["id"],
    ]

    swapped = await core_api.client.put(
        "/api/v1/admin/portfolio/projects/featured-order",
        headers=core_api.mutation_headers,
        json={"project_ids": [second["id"], first["id"]]},
    )
    assert swapped.status_code == 200, swapped.text
    assert [(item["id"], item["featured_rank"]) for item in swapped.json()] == [
        (second["id"], 1),
        (first["id"], 2),
    ]

    archived = await core_api.client.put(
        f"/api/v1/admin/portfolio/projects/{second['id']}/status",
        headers=core_api.mutation_headers,
        json={"status": "archived"},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["featured_rank"] is None

    replacement = await create_project("archive-replacement", rank=1)
    restored = await core_api.client.put(
        f"/api/v1/admin/portfolio/projects/{second['id']}/status",
        headers=core_api.mutation_headers,
        json={"status": "published"},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["featured_rank"] is None

    reclaim_conflict = await core_api.client.patch(
        f"/api/v1/admin/portfolio/projects/{second['id']}",
        headers=core_api.mutation_headers,
        json={"featured_rank": 1},
    )
    assert reclaim_conflict.status_code == 409
    assert "featured slot is occupied" in reclaim_conflict.json()["error"]["message"]

    hidden = await core_api.client.patch(
        f"/api/v1/admin/portfolio/projects/{first['id']}",
        headers=core_api.mutation_headers,
        json={"is_visible": False},
    )
    assert hidden.status_code == 200, hidden.text
    assert hidden.json()["featured_rank"] is None
    hidden_replacement = await create_project("hidden-replacement", rank=2)

    too_many = await core_api.client.put(
        "/api/v1/admin/portfolio/projects/featured-order",
        headers=core_api.mutation_headers,
        json={
            "project_ids": [
                replacement["id"],
                hidden_replacement["id"],
                draft["id"],
                second["id"],
            ]
        },
    )
    assert too_many.status_code == 422


@pytest.mark.asyncio
async def test_concurrent_featured_slot_assignment_has_one_winner(
    core_api: CoreAPI,
) -> None:
    project_ids: list[str] = []
    for index in range(2):
        response = await core_api.client.post(
            "/api/v1/admin/portfolio/projects",
            headers=core_api.mutation_headers,
            json={
                "title": f"Concurrent candidate {index}",
                "slug": f"concurrent-candidate-{index}",
                "summary": "A candidate awaiting an active presentation slot.",
                "featured_rank": 1,
                "status": "draft",
            },
        )
        assert response.status_code == 201, response.text
        project_ids.append(response.json()["id"])

    async def publish(project_id: str) -> httpx.Response:
        return await core_api.client.put(
            f"/api/v1/admin/portfolio/projects/{project_id}/status",
            headers=core_api.mutation_headers,
            json={"status": "published"},
        )

    results = await asyncio.gather(*(publish(project_id) for project_id in project_ids))
    assert sorted(response.status_code for response in results) == [200, 409]
    loser = next(response for response in results if response.status_code == 409)
    assert "featured slot is occupied" in loser.json()["error"]["message"]

    public = await core_api.client.get("/api/v1/public/projects?featured_only=true")
    assert public.status_code == 200
    assert public.json()["total"] == 1
    assert len(public.json()["items"]) == 1


@pytest.mark.asyncio
async def test_runtime_cap_prevents_dead_assistant_entry_point(core_api: CoreAPI) -> None:
    feature = await core_api.client.put(
        "/api/v1/admin/content/features",
        headers=core_api.mutation_headers,
        json={"key": "assistant", "enabled": True},
    )
    assert feature.status_code == 200
    section = await core_api.client.post(
        "/api/v1/admin/content/sections",
        headers=core_api.mutation_headers,
        json={
            "section_type": "assistant",
            "position": 1,
            "feature_key": "assistant",
            "status": "published",
        },
    )
    assert section.status_code == 201, section.text

    homepage = await core_api.client.get("/api/v1/public/homepage")

    assert homepage.status_code == 200
    assert homepage.json()["features"]["assistant"] is False
    assert homepage.json()["sections"] == []


@pytest.mark.asyncio
async def test_homepage_composition_is_atomic_and_exposes_safe_runtime_configuration(
    core_api: CoreAPI,
) -> None:
    feature = await core_api.client.put(
        "/api/v1/admin/content/features",
        headers=core_api.mutation_headers,
        json={
            "key": "assistant",
            "enabled": True,
            "configuration": {
                "greeting": "Ask about published test evidence.",
                "suggested_questions": ["Which project proves the integration?"],
                "disclaimer": "Published evidence only.",
                "max_question_length": 1000,
            },
        },
    )
    assert feature.status_code == 200, feature.text

    first = await core_api.client.put(
        "/api/v1/admin/content/sections/composition",
        headers=core_api.mutation_headers,
        json={
            "sections": [
                {
                    "section_type": "hero",
                    "position": 0,
                    "variant": "portrait",
                },
                {
                    "section_type": "editorial",
                    "position": 1,
                    "variant": "split",
                    "configuration": {
                        "blocks": [
                            {
                                "id": "editorial-proof",
                                "title": "Canonical composition",
                                "body": "The section payload survives the complete API round trip.",
                            }
                        ]
                    },
                },
            ]
        },
    )
    assert first.status_code == 200, first.text
    assert [item["position"] for item in first.json()] == [0, 1]
    editorial = first.json()[1]

    replacement = await core_api.client.put(
        "/api/v1/admin/content/sections/composition",
        headers=core_api.mutation_headers,
        json={
            "sections": [
                {
                    "id": editorial["id"],
                    "section_type": "editorial",
                    "position": 0,
                    "variant": "split",
                    "configuration": editorial["configuration"],
                }
            ]
        },
    )
    assert replacement.status_code == 200, replacement.text
    assert replacement.json()[0]["position"] == 0

    admin_sections = await core_api.client.get("/api/v1/admin/content/sections?limit=100&offset=0")
    assert admin_sections.status_code == 200
    assert admin_sections.json()["total"] == 2
    assert {item["status"] for item in admin_sections.json()["items"]} == {
        "archived",
        "published",
    }

    homepage = await core_api.client.get("/api/v1/public/homepage")
    assert homepage.status_code == 200
    body = homepage.json()
    assert body["sections"][0]["data"]["blocks"][0]["id"] == "editorial-proof"
    assert body["features"]["assistant"] is False
    assert body["feature_configurations"]["assistant"] == {
        "greeting": "Ask about published test evidence.",
        "suggested_questions": ["Which project proves the integration?"],
        "disclaimer": "Published evidence only.",
        "max_question_length": core_api.settings.assistant_max_question_chars,
    }


@pytest.mark.asyncio
async def test_project_media_uses_managed_storage_and_publication_privacy(
    core_api: CoreAPI,
    png_bytes: bytes,
) -> None:
    project = await core_api.client.post(
        "/api/v1/admin/portfolio/projects",
        headers=core_api.mutation_headers,
        json={
            "title": "Managed media project",
            "slug": "managed-media-project",
            "summary": "A test project with persisted managed media.",
            "status": "published",
        },
    )
    assert project.status_code == 201, project.text

    image = png_bytes
    upload = await core_api.client.post(
        "/api/v1/admin/portfolio/project-media/upload",
        headers=core_api.mutation_headers,
        data={
            "project_id": project.json()["id"],
            "alt_text": "Managed project architecture diagram",
            "caption": "Persisted through the configured storage adapter.",
            "sort_order": "0",
            "is_visible": "true",
        },
        files={"file": ("architecture.png", image, "image/png")},
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["external_url"] is None
    assert upload.json()["sha256"]
    assert (upload.json()["width"], upload.json()["height"]) == (1, 1)

    mismatched_metadata = await core_api.client.post(
        "/api/v1/admin/portfolio/project-media/upload",
        headers=core_api.mutation_headers,
        data={
            "project_id": project.json()["id"],
            "alt_text": "Incorrect client dimensions",
            "width": "2",
            "height": "1",
        },
        files={"file": ("mismatch.png", image, "image/png")},
    )
    assert mismatched_metadata.status_code == 422

    corrupt_media = await core_api.client.post(
        "/api/v1/admin/portfolio/project-media/upload",
        headers=core_api.mutation_headers,
        data={"project_id": project.json()["id"], "alt_text": "Corrupt image"},
        files={"file": ("corrupt.png", b"\x89PNG\r\n\x1a\ntruncated", "image/png")},
    )
    assert corrupt_media.status_code == 422

    public_file = await core_api.client.get(f"/api/v1/public/project-media/{upload.json()['id']}")
    assert public_file.status_code == 200
    assert public_file.content == image
    assert public_file.headers["etag"] == f'"{upload.json()["sha256"]}"'
    assert public_file.headers["accept-ranges"] == "bytes"

    partial_file = await core_api.client.get(
        f"/api/v1/public/project-media/{upload.json()['id']}",
        headers={"Range": "bytes=0-7"},
    )
    assert partial_file.status_code == 206
    assert partial_file.content == image[:8]
    assert partial_file.headers["content-range"] == f"bytes 0-7/{len(image)}"
    invalid_range = await core_api.client.get(
        f"/api/v1/public/project-media/{upload.json()['id']}",
        headers={"Range": "bytes=0-1,4-5"},
    )
    assert invalid_range.status_code == 416

    public_project = await core_api.client.get("/api/v1/public/projects/managed-media-project")
    assert public_project.status_code == 200
    assert public_project.json()["media"][0]["id"] == upload.json()["id"]

    discovery = await core_api.client.get(
        "/api/v1/discovery/page", params={"path": "/projects/managed-media-project"}
    )
    assert discovery.status_code == 200, discovery.text
    graph = discovery.json()["json_ld"]["@graph"]
    primary = next(item for item in graph if item.get("@type") == "CreativeWork")
    managed_media_url = (
        f"{str(core_api.settings.public_base_url).rstrip('/')}/api/v1/public/project-media/"
        f"{upload.json()['id']}"
    )
    assert primary["image"] == managed_media_url
    assert discovery.json()["metadata"]["open_graph"]["images"] == [managed_media_url]

    archived = await core_api.client.delete(
        f"/api/v1/admin/portfolio/project-media/{upload.json()['id']}",
        headers=core_api.mutation_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["is_visible"] is False
    assert (
        await core_api.client.get(f"/api/v1/public/project-media/{upload.json()['id']}")
    ).status_code == 404
    assert (await core_api.client.get("/api/v1/public/projects/managed-media-project")).json()[
        "media"
    ] == []


@pytest.mark.asyncio
async def test_repository_metadata_refresh_is_cached_fail_safe_and_publicly_fresh(
    core_api: CoreAPI,
    database_client: DatabaseClient,
) -> None:
    invalid_opt_in = await core_api.client.post(
        "/api/v1/admin/portfolio/projects",
        headers=core_api.mutation_headers,
        json={
            "title": "Invalid metadata opt in",
            "slug": "invalid-metadata-opt-in",
            "summary": "A non-open project cannot start external repository refreshes.",
            "repository_url": "https://github.com/example/private",
            "repository_metadata_refresh_enabled": True,
        },
    )
    assert invalid_opt_in.status_code == 422

    project = await core_api.client.post(
        "/api/v1/admin/portfolio/projects",
        headers=core_api.mutation_headers,
        json={
            "title": "Source project",
            "slug": "source-project",
            "summary": "An open-source project with reviewed repository signals.",
            "repository_url": "https://github.com/example/source-project",
            "is_open_source": True,
            "repository_metadata_refresh_enabled": True,
            "status": "published",
        },
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]
    assert project.json()["nature"] == "software"

    refreshed = await core_api.client.post(
        f"/api/v1/admin/portfolio/projects/{project_id}/repository-metadata/refresh",
        headers=core_api.mutation_headers,
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["status"] == "fresh"
    assert refreshed.json()["stars"] == 42
    assert len(core_api.repository_client.calls) == 1

    cached = await core_api.client.post(
        f"/api/v1/admin/portfolio/projects/{project_id}/repository-metadata/refresh",
        headers=core_api.mutation_headers,
    )
    assert cached.status_code == 200
    assert len(core_api.repository_client.calls) == 1

    public_project = await core_api.client.get("/api/v1/public/projects/source-project")
    metadata = public_project.json()["repository_metadata"]
    assert metadata == {
        "provider": "github",
        "repository_identity": "example/source-project",
        "language": "Python",
        "stars": 42,
        "forks": 7,
        "fetched_at": metadata["fetched_at"],
        "freshness": "fresh",
    }

    core_api.repository_client.results.append(
        RepositoryMetadataProviderError("rate_limited", retry_after_seconds=60)
    )
    rate_limited = await core_api.client.post(
        f"/api/v1/admin/portfolio/projects/{project_id}/repository-metadata/refresh?force=true",
        headers=core_api.mutation_headers,
    )
    assert rate_limited.status_code == 200
    assert rate_limited.json()["status"] == "rate_limited"
    assert rate_limited.json()["last_error_code"] == "rate_limited"
    assert rate_limited.json()["stars"] == 42
    assert (await core_api.client.get("/api/v1/public/projects/source-project")).json()[
        "repository_metadata"
    ]["freshness"] == "stale"

    calls_after_rate_limit = len(core_api.repository_client.calls)
    retry_suppressed = await core_api.client.post(
        f"/api/v1/admin/portfolio/projects/{project_id}/repository-metadata/refresh?force=true",
        headers=core_api.mutation_headers,
    )
    assert retry_suppressed.status_code == 200
    assert retry_suppressed.json()["status"] == "rate_limited"
    assert len(core_api.repository_client.calls) == calls_after_rate_limit

    # Expire the provider window explicitly before exercising a new provider result.
    async with database_client.session_factory() as session:
        await session.execute(
            update(RepositoryMetadataSnapshot)
            .where(RepositoryMetadataSnapshot.project_id == UUID(project_id))
            .values(retry_after=datetime.now(UTC) - timedelta(seconds=1))
        )
        await session.commit()

    core_api.repository_client.results.append(
        RepositoryMetadataProviderError("not_found_or_private")
    )
    unavailable = await core_api.client.post(
        f"/api/v1/admin/portfolio/projects/{project_id}/repository-metadata/refresh?force=true",
        headers=core_api.mutation_headers,
    )
    assert unavailable.status_code == 200
    assert unavailable.json()["last_error_code"] == "not_found_or_private"
    assert unavailable.json()["stars"] == 42

    changed = await core_api.client.patch(
        f"/api/v1/admin/portfolio/projects/{project_id}",
        headers=core_api.mutation_headers,
        json={"repository_url": "https://github.com/example/replacement"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["repository_metadata"]["fetched_at"] is None
    assert (await core_api.client.get("/api/v1/public/projects/source-project")).json()[
        "repository_metadata"
    ] is None


@pytest.mark.asyncio
async def test_remaining_core_resources_support_admin_and_public_lifecycles(
    core_api: CoreAPI,
    png_bytes: bytes,
) -> None:
    profile = await _create_profile(core_api)
    png = png_bytes
    portrait = await core_api.client.post(
        "/api/v1/admin/identity/portraits",
        headers=core_api.mutation_headers,
        data={
            "profile_id": profile["id"],
            "alt_text": "Professional portrait",
            "make_primary": "true",
        },
        files={"file": ("portrait.png", png, "image/png")},
    )
    assert portrait.status_code == 201, portrait.text
    portrait_file = await core_api.client.get(f"/api/v1/public/portraits/{portrait.json()['id']}")
    assert portrait_file.status_code == 200
    assert portrait_file.content == png

    social = await core_api.client.post(
        "/api/v1/admin/identity/social-links",
        headers=core_api.mutation_headers,
        json={
            "profile_id": profile["id"],
            "platform": "github",
            "label": "GitHub",
            "url": "https://github.com/example",
        },
    )
    assert social.status_code == 201
    social_update = await core_api.client.patch(
        f"/api/v1/admin/identity/social-links/{social.json()['id']}",
        headers=core_api.mutation_headers,
        json={"label": "Source code"},
    )
    assert social_update.status_code == 200
    assert social_update.json()["label"] == "Source code"

    category = await core_api.client.post(
        "/api/v1/admin/portfolio/categories",
        headers=core_api.mutation_headers,
        json={
            "name": "Platforms",
            "slug": "platforms",
            "description": "Platform engineering and architecture.",
            "status": "published",
        },
    )
    sector = await core_api.client.post(
        "/api/v1/admin/portfolio/sectors",
        headers=core_api.mutation_headers,
        json={
            "name": "Technology",
            "slug": "technology",
            "description": "Technology sector delivery.",
            "status": "published",
        },
    )
    assert category.status_code == sector.status_code == 201
    skill = await core_api.client.post(
        "/api/v1/admin/portfolio/skills",
        headers=core_api.mutation_headers,
        json={
            "category_id": category.json()["id"],
            "name": "FastAPI",
            "slug": "fastapi",
            "description": "Production API engineering.",
            "status": "published",
        },
    )
    assert skill.status_code == 201, skill.text
    assert skill.json()["category"]["id"] == category.json()["id"]

    project = await core_api.client.post(
        "/api/v1/admin/portfolio/projects",
        headers=core_api.mutation_headers,
        json={
            "category_id": category.json()["id"],
            "title": "Platform API",
            "slug": "platform-api",
            "summary": "A production API platform.",
            "skill_ids": [skill.json()["id"]],
            "sector_ids": [sector.json()["id"]],
            "status": "published",
        },
    )
    assert project.status_code == 201, project.text

    experience = await core_api.client.post(
        "/api/v1/admin/portfolio/experiences",
        headers=core_api.mutation_headers,
        json={
            "organization": "Example Organization",
            "role": "Lead Engineer",
            "start_date": "2024-01-01",
            "summary": "Led production platform delivery.",
            "achievements": ["Shipped the platform safely."],
            "skill_ids": [skill.json()["id"]],
            "sector_ids": [sector.json()["id"]],
            "project_ids": [project.json()["id"]],
            "status": "published",
        },
    )
    education = await core_api.client.post(
        "/api/v1/admin/portfolio/education",
        headers=core_api.mutation_headers,
        json={
            "institution": "Example University",
            "credential": "BSc Software Engineering",
            "start_date": "2018-01-01",
            "end_date": "2022-01-01",
            "status": "published",
        },
    )
    certification = await core_api.client.post(
        "/api/v1/admin/portfolio/certifications",
        headers=core_api.mutation_headers,
        json={
            "name": "Platform Architecture",
            "issuer": "Example Institute",
            "issued_on": "2025-01-01",
            "status": "published",
        },
    )
    assert experience.status_code == education.status_code == certification.status_code == 201
    invalid_dates = await core_api.client.patch(
        f"/api/v1/admin/portfolio/certifications/{certification.json()['id']}",
        headers=core_api.mutation_headers,
        json={"expires_on": "2024-01-01"},
    )
    assert invalid_dates.status_code == 422
    assert len((await core_api.client.get("/api/v1/public/experiences")).json()) == 1
    assert len((await core_api.client.get("/api/v1/public/education")).json()) == 1
    assert len((await core_api.client.get("/api/v1/public/certifications")).json()) == 1

    project_media = await core_api.client.post(
        "/api/v1/admin/portfolio/project-media",
        headers=core_api.mutation_headers,
        json={
            "project_id": project.json()["id"],
            "external_url": "https://cdn.example.com/project.png",
            "media_type": "image/png",
            "alt_text": "Project architecture",
        },
    )
    assert project_media.status_code == 201
    media_update = await core_api.client.patch(
        f"/api/v1/admin/portfolio/project-media/{project_media.json()['id']}",
        headers=core_api.mutation_headers,
        json={"caption": "Updated architecture caption"},
    )
    assert media_update.status_code == 200

    public_sectors = await core_api.client.get("/api/v1/public/sectors")
    assert public_sectors.status_code == 200
    assert public_sectors.json()[0]["project_count"] == 1

    testimonial = await core_api.client.post(
        "/api/v1/admin/portfolio/testimonials",
        headers=core_api.mutation_headers,
        json={
            "project_id": project.json()["id"],
            "quote": "A strong, verified delivery partner.",
            "attribution_name": "Reference Person",
            "evidence": {
                "kind": "document_reference",
                "visibility": "private_review",
                "reference_text": "Verified recommendation export",
                "provenance": "Owner-reviewed recommendation export",
                "captured_at": "2026-08-01",
            },
            "status": "published",
        },
    )
    assert testimonial.status_code == 201
    assert (await core_api.client.get("/api/v1/public/testimonials")).json() == []
    approved_testimonial = await core_api.client.put(
        f"/api/v1/admin/portfolio/testimonials/{testimonial.json()['id']}/approval",
        headers=core_api.mutation_headers,
    )
    assert approved_testimonial.status_code == 200
    assert len((await core_api.client.get("/api/v1/public/testimonials")).json()) == 1

    media_asset = await core_api.client.post(
        "/api/v1/admin/content/media",
        headers=core_api.mutation_headers,
        data={"alt_text": "Article hero"},
        files={"file": ("hero.png", png, "image/png")},
    )
    assert media_asset.status_code == 201, media_asset.text
    media_status = await core_api.client.put(
        f"/api/v1/admin/content/media/{media_asset.json()['id']}/status",
        headers=core_api.mutation_headers,
        json={"status": "published"},
    )
    assert media_status.status_code == 200
    media_metadata = await core_api.client.patch(
        f"/api/v1/admin/content/media/{media_asset.json()['id']}",
        headers=core_api.mutation_headers,
        json={"caption": "Published hero"},
    )
    assert media_metadata.status_code == 200

    document_asset = await core_api.client.post(
        "/api/v1/admin/content/media",
        headers=core_api.mutation_headers,
        data={"alt_text": "Supporting document"},
        files={"file": ("evidence.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
    )
    assert document_asset.status_code == 201, document_asset.text
    invalid_hero = await core_api.client.post(
        "/api/v1/admin/content/articles",
        headers=core_api.mutation_headers,
        json={
            "hero_media_id": document_asset.json()["id"],
            "title": "Invalid document hero",
            "slug": "invalid-document-hero",
            "excerpt": "Documents cannot be used as article hero images.",
            "body_markdown": "Hero validation must fail closed.",
            "topics": ["validation"],
            "status": "draft",
        },
    )
    assert invalid_hero.status_code == 422
    assert invalid_hero.json()["error"]["code"] == "validation_error"

    article = await core_api.client.post(
        "/api/v1/admin/content/articles",
        headers=core_api.mutation_headers,
        json={
            "hero_media_id": media_asset.json()["id"],
            "title": "Building a production platform",
            "slug": "building-a-production-platform",
            "excerpt": "A concise platform engineering case study.",
            "body_markdown": "# Production platform\n\nEvidence-backed details.",
            "topics": ["platforms", "api"],
            "status": "published",
        },
    )
    assert article.status_code == 201, article.text
    assert article.json()["hero_media"]["id"] == media_asset.json()["id"]
    public_article = await core_api.client.get(
        "/api/v1/public/articles/building-a-production-platform"
    )
    assert public_article.status_code == 200

    navigation = await core_api.client.post(
        "/api/v1/admin/content/navigation",
        headers=core_api.mutation_headers,
        json={
            "label": "Writing",
            "href": "/writing",
            "location": "header",
            "status": "published",
        },
    )
    assert navigation.status_code == 201
    footer_navigation = await core_api.client.post(
        "/api/v1/admin/content/navigation",
        headers=core_api.mutation_headers,
        json={
            "label": "Source",
            "href": "https://github.com/example",
            "location": "footer",
            "sort_order": 1,
            "open_in_new_tab": True,
            "status": "published",
        },
    )
    assert footer_navigation.status_code == 201
    public_navigation = (await core_api.client.get("/api/v1/public/navigation")).json()
    assert {(item["label"], item["location"]) for item in public_navigation} == {
        ("Writing", "header"),
        ("Source", "footer"),
    }
    shell_navigation = (await core_api.client.get("/api/v1/public/site-shell")).json()["navigation"]
    assert {(item["label"], item["location"]) for item in shell_navigation} == {
        ("Writing", "header"),
        ("Source", "footer"),
    }

    archive_article = await core_api.client.put(
        f"/api/v1/admin/content/articles/{article.json()['id']}/status",
        headers=core_api.mutation_headers,
        json={"status": "archived"},
    )
    assert archive_article.status_code == 200
    assert (
        await core_api.client.get("/api/v1/public/articles/building-a-production-platform")
    ).status_code == 404

    deleted_social = await core_api.client.delete(
        f"/api/v1/admin/identity/social-links/{social.json()['id']}",
        headers=core_api.mutation_headers,
    )
    assert deleted_social.status_code == 200


@pytest.mark.asyncio
async def test_public_collection_projections_meet_query_size_and_latency_budgets(
    core_api: CoreAPI,
    database_client: DatabaseClient,
) -> None:
    article_sentinel = "ARTICLE_BODY_MUST_NOT_REACH_COLLECTIONS"
    body = f"# Large article\n\n{article_sentinel}\n\n" + ("bounded content " * 9_000)
    article = await core_api.client.post(
        "/api/v1/admin/content/articles",
        headers=core_api.mutation_headers,
        json={
            "title": "Bounded article summary",
            "slug": "bounded-article-summary",
            "excerpt": "The collection returns only the bounded editorial summary.",
            "body_markdown": body,
            "topics": ["performance", "bounded-reads"],
            "status": "published",
        },
    )
    assert article.status_code == 201, article.text

    project_sentinel = "PROJECT_NARRATIVE_MUST_NOT_REACH_COLLECTIONS"
    for index in range(3):
        project = await core_api.client.post(
            "/api/v1/admin/portfolio/projects",
            headers=core_api.mutation_headers,
            json={
                "title": f"Bounded project {index}",
                "slug": f"bounded-project-{index}",
                "summary": f"Compact project summary {index}.",
                "description": project_sentinel + (" detailed narrative" * 2_000),
                "problem": "problem " * 2_000,
                "solution": "solution " * 2_000,
                "architecture": "architecture " * 1_500,
                "status": "published",
            },
        )
        assert project.status_code == 201, project.text

    engine = database_client.engine.sync_engine

    async def measured_get(path: str) -> tuple[httpx.Response, int, float]:
        statements: list[str] = []

        def record_query(
            _connection: Any,
            _cursor: Any,
            statement: str,
            _parameters: Any,
            _context: Any,
            _executemany: bool,
        ) -> None:
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(engine, "before_cursor_execute", record_query)
        started = time.perf_counter()
        try:
            response = await core_api.client.get(path)
        finally:
            elapsed = time.perf_counter() - started
            event.remove(engine, "before_cursor_execute", record_query)
        return response, len(statements), elapsed

    article_page, article_queries, article_elapsed = await measured_get(
        "/api/v1/public/articles?limit=20"
    )
    assert article_page.status_code == 200, article_page.text
    assert article_sentinel not in article_page.text
    assert "body_markdown" not in article_page.text
    assert len(article_page.content) < 30_000
    assert article_queries <= 3
    assert article_elapsed < 3.0

    project_page, project_queries, project_elapsed = await measured_get(
        "/api/v1/public/projects?limit=20"
    )
    assert project_page.status_code == 200, project_page.text
    assert project_sentinel not in project_page.text
    assert all(
        field not in project_page.json()["items"][0]
        for field in (
            "description",
            "problem",
            "solution",
            "architecture",
            "features",
            "decisions",
            "tradeoffs",
            "challenges",
            "outcomes",
            "testimonials",
        )
    )
    assert len(project_page.content) < 50_000
    assert project_queries <= 8
    assert project_elapsed < 3.0


@pytest.mark.asyncio
async def test_growing_public_and_admin_collections_are_server_paginated_and_filtered(
    core_api: CoreAPI,
) -> None:
    for index, title in enumerate(
        ["Alpha platform", "Beta search target", "Gamma platform"],
        start=1,
    ):
        created = await core_api.client.post(
            "/api/v1/admin/portfolio/projects",
            headers=core_api.mutation_headers,
            json={
                "title": title,
                "slug": f"pagination-project-{index}",
                "summary": f"Published pagination evidence {index}.",
                "status": "published",
            },
        )
        assert created.status_code == 201, created.text

    project_page = await core_api.client.get("/api/v1/public/projects?limit=1&offset=1")
    assert project_page.status_code == 200
    assert project_page.json()["total"] == 3
    assert project_page.json()["limit"] == 1
    assert project_page.json()["offset"] == 1
    assert len(project_page.json()["items"]) == 1

    project_search = await core_api.client.get(
        "/api/v1/public/projects?limit=10&offset=0&search=Beta"
    )
    assert project_search.status_code == 200
    assert project_search.json()["total"] == 1
    assert project_search.json()["items"][0]["title"] == "Beta search target"

    admin_search = await core_api.client.get(
        "/api/v1/admin/portfolio/projects?limit=1&offset=0&search=platform&status=published"
    )
    assert admin_search.status_code == 200
    assert admin_search.json()["total"] == 2
    assert len(admin_search.json()["items"]) == 1

    for index, topics in enumerate((["platforms", "api"], ["ai"]), start=1):
        article = await core_api.client.post(
            "/api/v1/admin/content/articles",
            headers=core_api.mutation_headers,
            json={
                "title": f"Pagination article {index}",
                "slug": f"pagination-article-{index}",
                "excerpt": f"Article pagination evidence {index}.",
                "body_markdown": "# Evidence\n\nPublished pagination content.",
                "topics": topics,
                "status": "published",
            },
        )
        assert article.status_code == 201, article.text

    article_page = await core_api.client.get("/api/v1/public/articles?limit=1&offset=0&topic=ai")
    assert article_page.status_code == 200, article_page.text
    assert article_page.json()["total"] == 1
    assert article_page.json()["items"][0]["topics"] == ["ai"]
    assert article_page.json()["topics"] == ["ai", "api", "platforms"]


@pytest.mark.asyncio
async def test_login_throttle_applies_across_identifiers_for_one_ip(
    database_client: DatabaseClient,
    tmp_path: Path,
) -> None:
    settings = _settings(
        database_client,
        tmp_path / "throttle-media",
        login_max_failures=2,
    )
    app = create_app(settings, database_client=database_client)
    await _create_admin(app, database_client)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for email in ("first@example.com", "second@example.com"):
            rejected = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "Incorrect-Password-42!"},
            )
            assert rejected.status_code == 401
        throttled = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "Correct-Horse-42!"},
        )
    assert throttled.status_code == 429
    assert throttled.headers["retry-after"] == str(settings.login_window_seconds)


async def _login_from_ip(
    app: Any,
    *,
    ip: str,
    email: str,
    password: str,
) -> httpx.Response:
    transport = httpx.ASGITransport(
        app=app,
        raise_app_exceptions=False,
        client=(ip, 42_000),
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )


@pytest.mark.asyncio
async def test_remote_account_failures_never_lock_out_valid_owner_and_success_decays_account(
    database_client: DatabaseClient,
    tmp_path: Path,
) -> None:
    settings = _settings(
        database_client,
        tmp_path / "account-throttle-media",
        login_max_failures=3,
        login_account_delay_threshold=2,
        login_account_max_delay_seconds=4,
    )
    app = create_app(settings, database_client=database_client)
    await _create_admin(app, database_client)

    attacker_statuses = []
    for index in range(4):
        response = await _login_from_ip(
            app,
            ip=f"198.51.100.{index + 1}",
            email="owner@example.com",
            password="Incorrect-Password-42!",
        )
        attacker_statuses.append(response.status_code)
    assert attacker_statuses[0] == 401
    assert attacker_statuses[1:] == [429, 429, 429]

    recovered = await _login_from_ip(
        app,
        ip="203.0.113.10",
        email="owner@example.com",
        password="Correct-Horse-42!",
    )
    assert recovered.status_code == 200, recovered.text

    after_success = await _login_from_ip(
        app,
        ip="203.0.113.11",
        email="owner@example.com",
        password="Incorrect-Password-42!",
    )
    assert after_success.status_code == 401
    async with database_client.session_factory() as session:
        owner_failures = await session.scalar(
            select(func.count(LoginAttempt.id)).where(
                LoginAttempt.succeeded.is_(False),
            )
        )
        account_buckets = await session.scalar(
            select(func.count(RateLimitBucket.bucket_key)).where(
                RateLimitBucket.bucket_key.like("auth-account-failure:%")
            )
        )
    assert owner_failures == 1
    assert account_buckets == 1


@pytest.mark.asyncio
async def test_login_failure_window_expires_without_clearing_abusive_ip_on_success(
    database_client: DatabaseClient,
    tmp_path: Path,
) -> None:
    settings = _settings(
        database_client,
        tmp_path / "expiry-throttle-media",
        login_max_failures=2,
        login_window_seconds=60,
    )
    app = create_app(settings, database_client=database_client)
    await _create_admin(app, database_client)
    for email in ("first@example.com", "second@example.com"):
        response = await _login_from_ip(
            app,
            ip="192.0.2.50",
            email=email,
            password="Incorrect-Password-42!",
        )
        assert response.status_code == 401
    blocked = await _login_from_ip(
        app,
        ip="192.0.2.50",
        email="owner@example.com",
        password="Correct-Horse-42!",
    )
    assert blocked.status_code == 429

    expired_at = datetime.now(UTC) - timedelta(minutes=5)
    async with database_client.session_factory() as session:
        await session.execute(update(LoginAttempt).values(occurred_at=expired_at))
        await session.execute(
            update(RateLimitBucket).values(
                window_started_at=expired_at,
                updated_at=expired_at,
            )
        )
        await session.commit()
    recovered = await _login_from_ip(
        app,
        ip="192.0.2.50",
        email="owner@example.com",
        password="Correct-Horse-42!",
    )
    assert recovered.status_code == 200
    async with database_client.session_factory() as session:
        ip_bucket_count = await session.scalar(
            select(func.count(RateLimitBucket.bucket_key)).where(
                RateLimitBucket.bucket_key.like("auth-ip-failure:%")
            )
        )
    assert ip_bucket_count == 1


@pytest.mark.asyncio
async def test_concurrent_login_failures_use_atomic_ip_bucket(
    database_client: DatabaseClient,
    tmp_path: Path,
) -> None:
    settings = _settings(
        database_client,
        tmp_path / "concurrent-throttle-media",
        login_max_failures=2,
        login_account_delay_threshold=10,
    )
    app = create_app(settings, database_client=database_client)
    responses = await asyncio.gather(
        *(
            _login_from_ip(
                app,
                ip="192.0.2.99",
                email=f"unknown-{index}@example.com",
                password="Incorrect-Password-42!",
            )
            for index in range(6)
        )
    )
    statuses = [response.status_code for response in responses]
    assert statuses.count(401) == 2
    assert statuses.count(429) == 4
