from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from apps.api.auth.dependencies import get_current_admin
from apps.api.auth.schemas import AdminUserRead, LoginRequest, LoginResponse
from apps.api.auth.service import AuthService, CurrentAdmin
from apps.api.dependencies import get_auth_service
from packages.python.common.schemas import MessageResponse
from packages.python.common.settings import Settings

router = APIRouter(prefix="/api/v1/auth", tags=["admin-auth"])


def _set_auth_cookies(
    response: Response,
    settings: Settings,
    *,
    session_token: str,
    csrf_token: str,
) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        max_age=settings.session_ttl_seconds,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
        domain=settings.cookie_domain,
        httponly=True,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=settings.session_ttl_seconds,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
        domain=settings.cookie_domain,
        httponly=False,
    )


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        settings.csrf_cookie_name,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=False,
        samesite="strict",
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    client_ip = request.client.host if request.client else "unknown"
    authenticated = await auth.login(str(payload.email), payload.password, client_ip)
    settings: Settings = request.app.state.settings
    _set_auth_cookies(
        response,
        settings,
        session_token=authenticated.session_token,
        csrf_token=authenticated.csrf_token,
    )
    response.headers["Cache-Control"] = "no-store"
    return LoginResponse(
        admin=AdminUserRead.model_validate(authenticated.user),
        expires_at=authenticated.session.expires_at,
        csrf_token=authenticated.csrf_token,
    )


@router.get("/me", response_model=AdminUserRead)
async def me(
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> AdminUserRead:
    return AdminUserRead.model_validate(current.user)


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> MessageResponse:
    await auth.logout(current)
    _clear_auth_cookies(response, request.app.state.settings)
    return MessageResponse(message="Logged out.")
