from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from apps.api.auth.models import AdminRole
from packages.python.common.schemas import APIModel, EntityRead


def _validate_admin_password(value: str) -> str:
    classes = sum(
        (
            any(character.islower() for character in value),
            any(character.isupper() for character in value),
            any(character.isdigit() for character in value),
            any(not character.isalnum() for character in value),
        )
    )
    if classes < 3:
        raise ValueError("password must contain at least three character classes")
    return value


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class AdminUserRead(EntityRead):
    email: EmailStr
    display_name: str
    role: AdminRole
    is_active: bool
    last_login_at: datetime | None


class LoginResponse(APIModel):
    admin: AdminUserRead
    expires_at: datetime
    csrf_token: str


class CreateAdminInput(APIModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=256)
    role: AdminRole = AdminRole.OWNER

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_admin_password(value)


class AdminCredentialsUpdate(APIModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_admin_password(value)
