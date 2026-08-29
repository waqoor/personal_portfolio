from __future__ import annotations

import struct
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError as PydanticValidationError
from starlette.responses import StreamingResponse
from starlette.types import Message, Receive, Scope, Send

from apps.api.middleware import ContentLengthLimitMiddleware
from packages.python.clients.storage import LocalStorageClient
from packages.python.common.errors import RequestTooLargeError, ValidationError
from packages.python.common.http_files import storage_file_response
from packages.python.common.models import PublicationStatus
from packages.python.common.policies import PublicationPolicy
from packages.python.common.settings import Settings
from packages.python.common.uploads import (
    validate_declared_metadata,
    validate_generic_media,
    validate_image,
    validate_pdf,
)
from services.content.models import HomepageSectionType
from services.content.registry import HomepageSectionRegistry
from services.content.schemas import (
    FeatureSettingUpsert,
    HomepageSectionCreate,
    NavigationItemCreate,
)
from services.identity.schemas import ProfileCreate


class PublishableEntity:
    def __init__(self) -> None:
        self.status = PublicationStatus.DRAFT
        self.is_visible = False
        self.noindex = False
        self.published_at: datetime | None = None
        self.archived_at: datetime | None = None


def test_publication_policy_controls_every_publication_state() -> None:
    entity = PublishableEntity()

    PublicationPolicy.apply(entity, PublicationStatus.PUBLISHED)
    first_published_at = entity.published_at
    assert PublicationPolicy.is_public(entity)
    assert first_published_at is not None

    PublicationPolicy.apply(entity, PublicationStatus.HIDDEN)
    assert not PublicationPolicy.is_public(entity)
    hidden_archived_at = entity.archived_at
    assert hidden_archived_at is None

    PublicationPolicy.apply(entity, PublicationStatus.ARCHIVED)
    assert not entity.is_visible
    archived_at = entity.archived_at
    assert archived_at is not None

    PublicationPolicy.apply(entity, PublicationStatus.PUBLISHED)
    assert entity.published_at == first_published_at
    republished_archived_at = entity.archived_at
    assert republished_archived_at is None


def test_upload_validation_uses_content_signatures_and_bounds(png_bytes: bytes) -> None:
    png = png_bytes
    pdf = b"%PDF-1.7\nbody\n%%EOF"

    assert validate_image(png, "image/png", 1_024).extension == ".png"
    assert validate_pdf(pdf, "application/pdf", 1_024).extension == ".pdf"
    with pytest.raises(ValidationError):
        validate_image(b"not a png", "image/png", 1_024)
    with pytest.raises(ValidationError):
        validate_pdf(b"%PDF-1.7\ntruncated", "application/pdf", 1_024)
    with pytest.raises(ValidationError):
        validate_image(png, "image/png", 4)


def test_upload_validation_covers_every_supported_production_media_signature(
    png_bytes: bytes,
) -> None:
    jpeg = b"\xff\xd8\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xd9"
    webp_payload = (
        b"VP8X"
        + (10).to_bytes(4, "little")
        + b"\x00\x00\x00\x00"
        + b"\x00\x00\x00"
        + b"\x00\x00\x00"
    )
    webp = b"RIFF" + (len(webp_payload) + 4).to_bytes(4, "little") + b"WEBP" + webp_payload
    avif = (
        b"\x00\x00\x00\x18ftypavif"
        + b"\x00" * 12
        + b"\x00\x00\x00\x14ispe\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01"
        + b"\x00\x00\x00\x08meta\x00\x00\x00\x08mdat"
    )
    pdf = b"%PDF-1.7\ncontent\n%%EOF"
    mvhd_payload = b"\x00" * 12 + (1_000).to_bytes(4, "big") + (2_000).to_bytes(4, "big")
    mvhd = (8 + len(mvhd_payload)).to_bytes(4, "big") + b"mvhd" + mvhd_payload
    tkhd_payload = b"\x00" * 8 + (640 << 16).to_bytes(4, "big") + (360 << 16).to_bytes(4, "big")
    tkhd = (8 + len(tkhd_payload)).to_bytes(4, "big") + b"tkhd" + tkhd_payload
    mp4 = b"\x00\x00\x00\x10ftypisom\x00\x00\x00\x00" + mvhd + tkhd
    webm = (
        b"\x1aE\xdf\xa3"
        + b"\x2a\xd7\xb1\x83\x0f\x42\x40"
        + b"\x44\x89\x84"
        + struct.pack(">f", 1_000.0)
        + b"\xb0\x82\x02\x80"
        + b"\xba\x82\x01\x68"
    )

    assert validate_image(jpeg, "image/jpeg; charset=binary", 1024).extension == ".jpg"
    assert validate_image(webp, "image/webp", 1024).extension == ".webp"
    assert validate_image(avif, "image/avif", 1024).extension == ".avif"
    assert validate_generic_media(pdf, "application/pdf", 1024).extension == ".pdf"
    assert validate_generic_media(png_bytes, "image/png", 1024).content == png_bytes
    mp4_upload = validate_generic_media(mp4, "video/mp4", 1024)
    assert (mp4_upload.width, mp4_upload.height, mp4_upload.duration_seconds) == (640, 360, 2)
    webm_upload = validate_generic_media(webm, "video/webm", 1024)
    assert (webm_upload.width, webm_upload.height, webm_upload.duration_seconds) == (640, 360, 1)
    validate_declared_metadata(mp4_upload, width=640, height=360, duration_seconds=2)
    with pytest.raises(ValidationError):
        validate_declared_metadata(mp4_upload, width=1920, height=360, duration_seconds=2)

    invalid_cases: tuple[Callable[[], object], ...] = (
        lambda: validate_image(b"", "image/png", 1024),
        lambda: validate_image(jpeg, "image/gif", 1024),
        lambda: validate_image(b"RIFFinvalid", "image/webp", 1024),
        lambda: validate_image(b"\x00\x00\x00\x18ftypxxxx", "image/avif", 1024),
        lambda: validate_pdf(b"", "application/pdf", 1024),
        lambda: validate_pdf(pdf, "application/pdf", 4),
        lambda: validate_pdf(pdf, "text/plain", 1024),
        lambda: validate_generic_media(b"", "application/octet-stream", 1024),
        lambda: validate_generic_media(b"too-large", "application/octet-stream", 2),
        lambda: validate_generic_media(b"not-video", "video/mp4", 1024),
    )
    for validate in invalid_cases:
        with pytest.raises(ValidationError):
            validate()


@pytest.mark.asyncio
async def test_local_storage_is_atomic_and_path_contained(tmp_path: Path) -> None:
    storage = LocalStorageClient(tmp_path / "media")
    stored = await storage.save("portraits/primary.png", b"image-bytes")

    assert stored.sha256
    assert await storage.read(stored.key) == b"image-bytes"
    assert await storage.exists(stored.key)
    with pytest.raises(ValidationError):
        await storage.save("../outside.txt", b"blocked")

    await storage.delete(stored.key)
    assert not await storage.exists(stored.key)


@pytest.mark.asyncio
async def test_large_storage_response_is_bounded_streaming_not_a_full_object_read() -> None:
    class ChunkTrackingStorage:
        def __init__(self) -> None:
            self.read_called = False
            self.max_chunk_size = 0
            self.requested_range: tuple[int, int | None] | None = None

        async def read(self, key: str) -> bytes:
            del key
            self.read_called = True
            raise AssertionError("large-file delivery must never call the full-object reader")

        def iter_bytes(
            self,
            key: str,
            *,
            start: int = 0,
            end: int | None = None,
            chunk_size: int = 64 * 1024,
        ) -> AsyncIterator[bytes]:
            del key
            self.requested_range = (start, end)

            async def chunks() -> AsyncIterator[bytes]:
                remaining = 0 if end is None else end - start + 1
                while remaining:
                    emitted = min(chunk_size, remaining)
                    self.max_chunk_size = max(self.max_chunk_size, emitted)
                    remaining -= emitted
                    yield b"x" * emitted

            return chunks()

    size = 8 * 1024 * 1024 + 123
    storage = ChunkTrackingStorage()
    response = await storage_file_response(
        storage=storage,  # type: ignore[arg-type]
        key="documents/large.pdf",
        size=size,
        media_type="application/pdf",
        etag="a" * 64,
        range_header=None,
        cache_control="public, max-age=60",
    )

    assert isinstance(response, StreamingResponse)
    streamed_size = 0
    async for chunk in response.body_iterator:
        assert isinstance(chunk, bytes)
        streamed_size += len(chunk)
    assert streamed_size == size
    assert storage.requested_range == (0, size - 1)
    assert storage.max_chunk_size <= 64 * 1024
    assert storage.read_called is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "validator", ['"asset-etag"', 'W/"asset-etag"', '"other", "asset-etag"', "*"]
)
async def test_storage_response_honors_if_none_match_without_reading_storage(
    validator: str,
) -> None:
    class NeverReadStorage:
        def iter_bytes(
            self,
            key: str,
            *,
            start: int = 0,
            end: int | None = None,
            chunk_size: int = 64 * 1024,
        ) -> AsyncIterator[bytes]:
            del key, start, end, chunk_size
            raise AssertionError("a matching conditional request must not read storage")

    response = await storage_file_response(
        storage=NeverReadStorage(),  # type: ignore[arg-type]
        key="portraits/asset.png",
        size=128,
        media_type="image/png",
        etag="asset-etag",
        range_header=None,
        cache_control="public, max-age=86400, immutable",
        if_none_match=validator,
    )

    assert response.status_code == 304
    assert response.headers["etag"] == '"asset-etag"'
    assert response.headers["cache-control"] == "public, max-age=86400, immutable"
    assert "content-length" not in response.headers


def test_public_configuration_is_bounded_and_cannot_hold_credentials() -> None:
    valid = HomepageSectionCreate(
        section_type=HomepageSectionType.EDITORIAL,
        position=1,
        configuration={"eyebrow": "Evidence", "columns": ["one", "two"]},
    )
    assert valid.configuration["eyebrow"] == "Evidence"

    with pytest.raises(PydanticValidationError):
        HomepageSectionCreate(
            section_type=HomepageSectionType.EDITORIAL,
            position=1,
            configuration={"provider_api_key": "must-not-be-public"},
        )
    with pytest.raises(PydanticValidationError):
        FeatureSettingUpsert(
            key="assistant.enabled",
            configuration={"nested": {"access-token": "secret"}},
        )


@pytest.mark.parametrize(
    "href",
    ["https:relative", "https://user:password@example.com/path", "javascript:alert(1)"],
)
def test_navigation_rejects_unsafe_or_malformed_targets(href: str) -> None:
    with pytest.raises(PydanticValidationError):
        NavigationItemCreate(label="Unsafe", href=href)


def test_featured_project_default_is_explicit_and_configurable() -> None:
    assert HomepageSectionRegistry().default_limit(HomepageSectionType.SELECTED_WORK) == 5
    assert HomepageSectionRegistry(3).default_limit(HomepageSectionType.SELECTED_WORK) == 3
    assert HomepageSectionRegistry().feature_key(HomepageSectionType.SELECTED_WORK) == "projects"


def test_profile_cta_requires_a_complete_safe_label_and_url_pair() -> None:
    base = {
        "full_name": "Portfolio owner",
        "headline": "Production engineer",
        "short_bio": "Public profile used to validate CTA contracts.",
    }
    with pytest.raises(PydanticValidationError):
        ProfileCreate(**base, primary_cta_label="View work")
    with pytest.raises(PydanticValidationError):
        ProfileCreate(**base, primary_cta_url="/projects")
    parsed = ProfileCreate(
        **base,
        primary_cta_label="View work",
        primary_cta_url="/projects",
    )
    assert parsed.primary_cta_url == "/projects"


def test_production_settings_reject_insecure_origins_and_placeholders() -> None:
    base: dict[str, Any] = {
        "_env_file": None,
        "environment": "production",
        "database_url": "postgresql+asyncpg://portfolio:unique-db-secret-2026@db/portfolio",
        "auth_secret": "auth-secret-that-is-long-and-production-unique",
        "privacy_hash_secret": "privacy-secret-that-is-long-and-production-unique",
        "cookie_secure": True,
        "public_base_url": "https://portfolio.example",
        "api_public_url": "https://api.portfolio.example",
        "allowed_origins": ["https://portfolio.example"],
        "allowed_hosts": ["api.portfolio.example"],
        "docs_enabled": False,
    }
    assert Settings(**base).environment == "production"
    with pytest.raises(PydanticValidationError):
        Settings(**{**base, "allowed_origins": ["http://portfolio.example"]})
    with pytest.raises(PydanticValidationError):
        Settings(
            **{
                **base,
                "database_url": ("postgresql+asyncpg://portfolio:CHANGE_ME@db/portfolio"),
            }
        )


def _secure_production_settings(**changes: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "environment": "production",
        "database_url": ("postgresql+asyncpg://portfolio:unique-db-secret-2026@db:5432/portfolio"),
        "auth_secret": "auth-secret-that-is-long-and-production-unique",
        "privacy_hash_secret": "privacy-secret-that-is-long-and-production-unique",
        "cookie_secure": True,
        "public_base_url": "https://portfolio.example",
        "api_public_url": "https://api.portfolio.example",
        "allowed_origins": ["https://portfolio.example"],
        "allowed_hosts": ["api.portfolio.example"],
        "forwarded_allow_ips": "172.16.0.0/12",
        "docs_enabled": False,
    }
    values.update(changes)
    return Settings(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "changes",
    [
        {"api_prefix": "api/v1"},
        {"api_prefix": "/api/v1/"},
        {"allowed_origins": []},
        {"allowed_origins": ["https://user:secret@portfolio.example"]},
        {"allowed_origins": ["https://portfolio.example/path"]},
        {"allowed_hosts": []},
        {"allowed_hosts": ["https://portfolio.example"]},
        {"verified_same_as_urls": ["http://social.example/owner"]},
        {"auth_secret": "short"},
        {"privacy_hash_secret": "short"},
        {
            "auth_secret": "same-secret-value-with-more-than-32-characters",
            "privacy_hash_secret": "same-secret-value-with-more-than-32-characters",
        },
        {"smtp_use_starttls": True, "smtp_use_ssl": True},
        {"email_enabled": True},
        {"assistant_enabled": True},
        {"api_public_url": "relative"},
        {"public_base_url": "ftp://portfolio.example"},
        {"public_base_url": "https://portfolio.example/base"},
        {"site_social_image_url": "javascript:alert(1)"},
        {"smtp_username": "user-without-password"},
    ],
)
def test_settings_reject_invalid_shared_configuration(changes: dict[str, object]) -> None:
    with pytest.raises(PydanticValidationError):
        _secure_production_settings(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"auth_secret": "development-only-secret-change-before-production"},
        {"privacy_hash_secret": "development-privacy-secret-change-before-production"},
        {"cookie_secure": False},
        {"public_base_url": "http://portfolio.example"},
        {"api_public_url": "http://api.portfolio.example"},
        {"allowed_origins": ["*"]},
        {"allowed_hosts": ["*"]},
        {"forwarded_allow_ips": "127.0.0.1,*"},
        {"database_url": ("postgresql://portfolio:unique-db-secret-2026@db:5432/portfolio")},
        {"database_url": "postgresql+asyncpg://portfolio:short@db:5432/portfolio"},
        {"database_url": ("postgresql+asyncpg://portfolio:password-password@db:5432/portfolio")},
        {"allowed_origins": ["http://portfolio.example"]},
        {
            "assistant_enabled": True,
            "ai_provider_api_key": "provider-secret",
            "ai_model": "provider-model",
            "ai_provider_base_url": "http://provider.example/v1/",
        },
        {
            "email_enabled": True,
            "smtp_host": "smtp.example.com",
            "email_from_address": "sender@example.com",
            "contact_notification_to": "owner@example.com",
            "smtp_use_starttls": False,
            "smtp_use_ssl": False,
        },
        {"content_security_policy": ""},
        {"docs_enabled": True},
    ],
)
def test_production_settings_fail_closed(changes: dict[str, object]) -> None:
    with pytest.raises(PydanticValidationError):
        _secure_production_settings(**changes)


def test_settings_require_postgresql_outside_tests() -> None:
    with pytest.raises(PydanticValidationError):
        Settings(
            _env_file=None,
            environment="development",
            database_url="sqlite+aiosqlite:///local.db",
            auth_secret="development-auth-secret-with-at-least-32-characters",
            privacy_hash_secret="development-privacy-secret-with-at-least-32-characters",
        )


@pytest.mark.asyncio
async def test_streamed_body_limit_does_not_trust_content_length() -> None:
    messages: AsyncIterator[Message]

    async def chunks() -> AsyncIterator[Message]:
        yield {"type": "http.request", "body": b"1234", "more_body": True}
        yield {"type": "http.request", "body": b"5678", "more_body": False}

    messages = chunks()

    async def receive() -> Message:
        return await anext(messages)

    async def send(message: Message) -> None:
        del message

    async def consume_body(
        scope: Scope,
        downstream_receive: Receive,
        downstream_send: Send,
    ) -> None:
        del scope, downstream_send
        while True:
            message = await downstream_receive()
            if not message.get("more_body"):
                break

    middleware = ContentLengthLimitMiddleware(consume_body, max_bytes=6)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/upload",
        "headers": [],
    }
    with pytest.raises(RequestTooLargeError):
        await middleware(scope, receive, send)
