from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from packages.python.common.models import PublicationStatus


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)


class ErrorItem(APIModel):
    location: list[str | int] = Field(default_factory=list)
    message: str
    type: str | None = None


class ErrorBody(APIModel):
    code: str
    message: str
    request_id: str
    details: list[ErrorItem] = Field(default_factory=list)


class ErrorEnvelope(APIModel):
    error: ErrorBody


class EntityRead(APIModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


class PublicationRead(APIModel):
    status: PublicationStatus
    is_visible: bool
    noindex: bool
    published_at: datetime | None
    archived_at: datetime | None


class PublicationUpdate(APIModel):
    status: PublicationStatus | None = None
    is_visible: bool | None = None
    noindex: bool | None = None


T = TypeVar("T")


class Page(APIModel, Generic[T]):  # noqa: UP046
    items: list[T]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class MessageResponse(APIModel):
    message: str


class HealthResponse(APIModel):
    status: str
    checks: dict[str, Any] | None = None


class LifecycleStatusInput(APIModel):
    status: PublicationStatus
