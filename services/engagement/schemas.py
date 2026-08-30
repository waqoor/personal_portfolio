"""Validated HTTP and application boundary schemas for engagement."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from packages.python.common.schemas import APIModel

ContactCategory = Literal["general", "project", "collaboration", "speaking", "sponsorship", "other"]


def is_github_sponsors_destination(value: str) -> bool:
    """Return whether a sponsorship destination keeps checkout on GitHub Sponsors."""

    try:
        parsed = urlsplit(value)
        path_segments = [segment for segment in parsed.path.split("/") if segment]
        return (
            parsed.scheme.casefold() == "https"
            and parsed.hostname == "github.com"
            and parsed.port in (None, 443)
            and parsed.username is None
            and parsed.password is None
            and len(path_segments) >= 2
            and path_segments[0].casefold() == "sponsors"
            and path_segments[1] not in {".", ".."}
        )
    except ValueError:
        return False


class ContactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    category: ContactCategory = "general"
    organization: str | None = Field(default=None, max_length=160)
    subject: str | None = Field(default=None, max_length=200)
    message: str = Field(min_length=20, max_length=5000)
    consent: Literal[True]
    website: str = Field(default="", max_length=200, repr=False)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if any(character in value for character in "\r\n\x00"):
            raise ValueError("Name contains invalid characters")
        return " ".join(value.split())

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if any(character in value for character in "\r\n\x00"):
            raise ValueError("Subject contains invalid characters")
        return " ".join(value.split()) or None

    @field_validator("organization")
    @classmethod
    def validate_organization(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if any(character in value for character in "\r\n\x00"):
            raise ValueError("Organization contains invalid characters")
        return " ".join(value.split()) or None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("Message contains invalid characters")
        return value.strip()


class ContactReceipt(BaseModel):
    accepted: Literal[True] = True
    reference_id: str
    accepted_at: datetime
    message: str = "Your message has been received."


class ContactNotificationBatchResult(APIModel):
    selected_count: int = Field(ge=0)
    sent_count: int = Field(ge=0)
    not_sent_by_this_worker_count: int = Field(ge=0)


class ContactCategoryOption(BaseModel):
    id: ContactCategory
    label: str


class ContactOptionsResponse(BaseModel):
    categories: list[ContactCategoryOption]
    response_time_label: str | None = None
    accepting_messages: bool


class SponsorshipOptionResponse(BaseModel):
    slug: str
    title: str
    description: str
    kind: str
    cta_label: str
    destination_url: str
    amount_minor: int | None = None
    currency: str | None = None
    recurrence: str | None = None
    rel: Literal["sponsored nofollow noopener", "noopener"]


class SponsorshipOptionsResponse(BaseModel):
    items: list[SponsorshipOptionResponse] = Field(max_length=20)


class SponsorshipOptionCreate(APIModel):
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=10_000)
    kind: str = Field(min_length=1, max_length=32)
    cta_label: str = Field(min_length=1, max_length=80)
    destination_url: HttpUrl
    amount_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    recurrence: Literal["one_time", "monthly", "yearly"] | None = None
    sort_order: int = Field(default=0, ge=0, le=100_000)
    is_published: bool = False
    nofollow: bool = True

    @field_validator("destination_url")
    @classmethod
    def require_https_destination(cls, value: HttpUrl) -> HttpUrl:
        if not is_github_sponsors_destination(str(value)):
            raise ValueError("sponsorship destinations must use a GitHub Sponsors HTTPS URL")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else None

    @model_validator(mode="after")
    def validate_amount_currency(self) -> SponsorshipOptionCreate:
        if (self.amount_minor is None) != (self.currency is None):
            raise ValueError("amount_minor and currency must be supplied together")
        return self


class SponsorshipOptionUpdate(APIModel):
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=10_000)
    kind: str | None = Field(default=None, min_length=1, max_length=32)
    cta_label: str | None = Field(default=None, min_length=1, max_length=80)
    destination_url: HttpUrl | None = None
    amount_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    recurrence: Literal["one_time", "monthly", "yearly"] | None = None
    sort_order: int | None = Field(default=None, ge=0, le=100_000)
    is_published: bool | None = None
    nofollow: bool | None = None

    _require_https_destination = field_validator("destination_url")(
        lambda value: (
            SponsorshipOptionCreate.require_https_destination(value) if value is not None else None
        )
    )
    _normalize_currency = field_validator("currency")(SponsorshipOptionCreate.normalize_currency)

    @model_validator(mode="after")
    def validate_amount_currency_update(self) -> SponsorshipOptionUpdate:
        amount_supplied = "amount_minor" in self.model_fields_set
        currency_supplied = "currency" in self.model_fields_set
        if amount_supplied != currency_supplied:
            raise ValueError("amount_minor and currency must be updated together")
        if amount_supplied and ((self.amount_minor is None) != (self.currency is None)):
            raise ValueError("amount_minor and currency must be supplied together")
        return self


class SponsorshipOptionAdminRead(APIModel):
    id: str
    slug: str
    title: str
    description: str
    kind: str
    cta_label: str
    destination_url: str
    amount_minor: int | None
    currency: str | None
    recurrence: str | None
    sort_order: int
    is_published: bool
    is_archived: bool
    nofollow: bool
    updated_at: datetime


class ContactSubmissionAdminRead(APIModel):
    id: str
    name: str
    email: EmailStr
    organization: str | None
    category: str
    subject: str | None
    message: str
    consent: bool
    status: str
    notification_status: str
    notification_error_code: str | None
    notification_attempt_count: int = Field(ge=0)
    notification_next_attempt_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ContactStatusUpdate(APIModel):
    status: Literal["new", "read", "closed", "spam"]
