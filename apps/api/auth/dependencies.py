from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, Request

from apps.api.auth.service import AuthService, CurrentAdmin
from apps.api.dependencies import get_auth_service
from packages.python.common.errors import ForbiddenError
from packages.python.common.models import PublicationStatus
from packages.python.common.settings import Settings


async def get_current_admin(
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> CurrentAdmin:
    settings: Settings = request.app.state.settings
    session_token = request.cookies.get(settings.session_cookie_name)
    csrf_token: str | None = None
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
        csrf_header = request.headers.get(settings.csrf_header_name)
        if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
            raise ForbiddenError("CSRF validation failed.")
        csrf_token = csrf_header
    current = await auth.authenticate(session_token, csrf_token)
    request.state.current_admin = current
    return current


async def get_owner_admin(
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> CurrentAdmin:
    AuthService.require_owner(current)
    return current


def require_owner_for_initial_status(current: CurrentAdmin, status: PublicationStatus) -> None:
    """Editors may author drafts; only owners may make content public at creation."""

    if status is not PublicationStatus.DRAFT:
        AuthService.require_owner(current)


def require_owner_for_publication_fields(
    current: CurrentAdmin, changed_fields: set[str], *, extra_fields: set[str] | None = None
) -> None:
    controlled = {"is_visible", "noindex"}
    if extra_fields:
        controlled.update(extra_fields)
    if changed_fields & controlled:
        AuthService.require_owner(current)
