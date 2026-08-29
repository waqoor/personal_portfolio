"""Liveness and dependency-aware readiness endpoints."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from packages.python.clients.ai import AIProviderClient
from packages.python.clients.database import DatabaseClient
from packages.python.clients.email import EmailClient

router = APIRouter(prefix="/health", tags=["operations"])


class HealthResponse(BaseModel):
    status: Literal["ok", "not_ready"]
    checks: dict[str, bool]


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok", checks={"process": True})


@router.get("/ready", response_model=HealthResponse)
async def readiness(request: Request) -> HealthResponse | JSONResponse:
    database: DatabaseClient = request.app.state.database_client
    checks = {"database": await database.health_check()}
    settings = request.app.state.settings
    if settings.readiness_check_email and settings.email_enabled:
        email_client: EmailClient | None = request.app.state.email_client
        checks["email"] = bool(email_client and await email_client.health_check())
    if settings.readiness_check_ai and settings.assistant_enabled:
        ai_client: AIProviderClient | None = request.app.state.ai_provider_client
        checks["ai"] = bool(ai_client and await ai_client.health_check())
    if all(checks.values()):
        return HealthResponse(status="ok", checks=checks)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=HealthResponse(status="not_ready", checks=checks).model_dump(),
        headers={"Retry-After": "5"},
    )
