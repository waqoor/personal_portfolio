from __future__ import annotations

from datetime import date
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import AfterValidator, EmailStr, Field, HttpUrl, TypeAdapter, model_validator

from packages.python.common.models import PublicationStatus
from packages.python.common.schemas import APIModel, EntityRead, PublicationRead

_EMAIL_ADAPTER = TypeAdapter(EmailStr)


def validate_public_link(value: str) -> str:
    """Accept local paths, HTTPS URLs, and mailto links without ambiguous authority."""

    value = value.strip()
    if not value or any(ord(character) < 32 for character in value) or "\\" in value:
        raise ValueError("link contains invalid characters")
    if value.startswith("/"):
        if value.startswith("//"):
            raise ValueError("protocol-relative links are not allowed")
        return value
    parsed = urlsplit(value)
    if parsed.scheme == "https":
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError("HTTPS links cannot contain credentials")
        return value
    if parsed.scheme == "mailto" and parsed.path and not parsed.query and not parsed.fragment:
        _EMAIL_ADAPTER.validate_python(parsed.path)
        return value
    raise ValueError("link must be a relative path, HTTPS URL, or mailto address")


PublicLink = Annotated[str, AfterValidator(validate_public_link)]


class ProfileBase(APIModel):
    full_name: str = Field(min_length=1, max_length=160)
    headline: str = Field(min_length=1, max_length=240)
    short_bio: str = Field(min_length=1, max_length=2_000)
    long_bio: str | None = Field(default=None, max_length=20_000)
    public_location: str | None = Field(default=None, max_length=160)
    availability_status: str | None = Field(default=None, max_length=80)
    availability_detail: str | None = Field(default=None, max_length=300)
    public_email: EmailStr | None = None
    primary_cta_label: str | None = Field(default=None, max_length=80)
    primary_cta_url: PublicLink | None = None
    secondary_cta_label: str | None = Field(default=None, max_length=80)
    secondary_cta_url: PublicLink | None = None

    @model_validator(mode="after")
    def validate_cta_pairs(self) -> ProfileBase:
        for name, label, url in (
            ("primary", self.primary_cta_label, self.primary_cta_url),
            ("secondary", self.secondary_cta_label, self.secondary_cta_url),
        ):
            if bool(label and label.strip()) != bool(url):
                raise ValueError(f"{name} CTA label and URL must be provided together")
        return self


class ProfileCreate(ProfileBase):
    is_primary: bool = False
    status: PublicationStatus = PublicationStatus.DRAFT
    is_visible: bool = True
    noindex: bool = False


class ProfileUpdate(APIModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    headline: str | None = Field(default=None, min_length=1, max_length=240)
    short_bio: str | None = Field(default=None, min_length=1, max_length=2_000)
    long_bio: str | None = Field(default=None, max_length=20_000)
    public_location: str | None = Field(default=None, max_length=160)
    availability_status: str | None = Field(default=None, max_length=80)
    availability_detail: str | None = Field(default=None, max_length=300)
    public_email: EmailStr | None = None
    primary_cta_label: str | None = Field(default=None, max_length=80)
    primary_cta_url: PublicLink | None = None
    secondary_cta_label: str | None = Field(default=None, max_length=80)
    secondary_cta_url: PublicLink | None = None
    is_primary: bool | None = None
    is_visible: bool | None = None
    noindex: bool | None = None


class PortraitRead(EntityRead):
    profile_id: UUID
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    alt_text: str
    width: int | None
    height: int | None
    is_primary: bool
    is_active: bool
    sort_order: int


class ResumeRead(EntityRead, PublicationRead):
    profile_id: UUID
    version_label: str
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    effective_date: date | None
    is_current: bool
    download_name: str


class PublicResumeRead(EntityRead):
    """Sanitized current résumé metadata bound to the selected public profile."""

    version_label: str
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    effective_date: date | None
    is_current: bool
    download_name: str


class SocialLinkBase(APIModel):
    platform: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=120)
    url: HttpUrl
    handle: str | None = Field(default=None, max_length=160)
    sort_order: int = Field(default=0, ge=0, le=10_000)
    is_visible: bool = True


class SocialLinkCreate(SocialLinkBase):
    profile_id: UUID


class SocialLinkUpdate(APIModel):
    platform: str | None = Field(default=None, min_length=1, max_length=80)
    label: str | None = Field(default=None, min_length=1, max_length=120)
    url: HttpUrl | None = None
    handle: str | None = Field(default=None, max_length=160)
    sort_order: int | None = Field(default=None, ge=0, le=10_000)
    is_visible: bool | None = None


class SocialLinkRead(EntityRead, SocialLinkBase):
    profile_id: UUID


class ProfileRead(EntityRead, PublicationRead, ProfileBase):
    is_primary: bool
    portraits: list[PortraitRead] = Field(default_factory=list)
    social_links: list[SocialLinkRead] = Field(default_factory=list)


class ResumeUploadMetadata(APIModel):
    profile_id: UUID
    version_label: str = Field(min_length=1, max_length=120)
    effective_date: date | None = None
    download_name: str = Field(default="resume.pdf", min_length=1, max_length=255)


class PortraitUploadMetadata(APIModel):
    profile_id: UUID
    alt_text: str = Field(min_length=1, max_length=300)
    width: int | None = Field(default=None, ge=1, le=50_000)
    height: int | None = Field(default=None, ge=1, le=50_000)
    sort_order: int = Field(default=0, ge=0, le=10_000)
    make_primary: bool = False
