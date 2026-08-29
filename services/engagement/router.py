"""FastAPI transport adapter for engagement services."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, Query, Request, status

from apps.api.auth.dependencies import get_current_admin, get_owner_admin
from apps.api.auth.service import CurrentAdmin
from packages.python.common.schemas import Page
from services.engagement.schemas import (
    ContactNotificationBatchResult,
    ContactOptionsResponse,
    ContactReceipt,
    ContactRequest,
    ContactStatusUpdate,
    ContactSubmissionAdminRead,
    SponsorshipOptionAdminRead,
    SponsorshipOptionCreate,
    SponsorshipOptionsResponse,
    SponsorshipOptionUpdate,
)
from services.engagement.service import (
    ContactRequestContext,
    ContactService,
    EngagementAdminService,
    SponsorshipService,
)

public_router = APIRouter(prefix="/api/v1", tags=["engagement"])
admin_router = APIRouter(
    prefix="/api/v1/admin/engagement",
    tags=["admin-engagement"],
    dependencies=[Depends(get_current_admin)],
)


def _contact_service(request: Request) -> ContactService:
    return cast(ContactService, request.app.state.contact_service)


def _sponsorship_service(request: Request) -> SponsorshipService:
    return cast(SponsorshipService, request.app.state.sponsorship_service)


def _admin_service(request: Request) -> EngagementAdminService:
    return cast(EngagementAdminService, request.app.state.engagement_admin_service)


@public_router.post(
    "/contact",
    response_model=ContactReceipt,
    status_code=status.HTTP_202_ACCEPTED,
    responses={429: {"description": "Rate limit exceeded"}},
)
async def submit_contact(
    payload: ContactRequest,
    request: Request,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=8, max_length=128),
    ] = None,
) -> ContactReceipt:
    client_ip = request.client.host if request.client else "unknown"
    return await _contact_service(request).submit(
        payload,
        ContactRequestContext(
            client_ip=client_ip,
            idempotency_key=idempotency_key,
        ),
    )


@public_router.get("/contact/options", response_model=ContactOptionsResponse)
async def contact_options(request: Request) -> ContactOptionsResponse:
    return await _contact_service(request).public_options()


@public_router.get("/sponsorship", response_model=SponsorshipOptionsResponse)
async def list_sponsorship_options(request: Request) -> SponsorshipOptionsResponse:
    return await _sponsorship_service(request).list_public_options()


@admin_router.get(
    "/contact-submissions",
    response_model=Page[ContactSubmissionAdminRead],
)
async def list_contact_submissions(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    status_filter: Annotated[str | None, Query(alias="status", max_length=24)] = None,
) -> Page[ContactSubmissionAdminRead]:
    return await _admin_service(request).list_contacts(
        limit=limit,
        offset=offset,
        search=search,
        status=status_filter,
    )


@admin_router.patch(
    "/contact-submissions/{submission_id}/status",
    response_model=ContactSubmissionAdminRead,
)
async def update_contact_submission_status(
    submission_id: str,
    payload: ContactStatusUpdate,
    request: Request,
) -> ContactSubmissionAdminRead:
    return await _admin_service(request).update_contact_status(submission_id, payload)


@admin_router.post(
    "/contact-submissions/{submission_id}/retry-notification",
    response_model=ContactSubmissionAdminRead,
)
async def retry_contact_notification(
    submission_id: str,
    request: Request,
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> ContactSubmissionAdminRead:
    del current
    return await _admin_service(request).retry_contact_notification(submission_id)


@admin_router.post(
    "/contact-notifications/process-due",
    response_model=ContactNotificationBatchResult,
)
async def process_due_contact_notifications(
    request: Request,
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ContactNotificationBatchResult:
    del current
    return await _contact_service(request).process_due_notifications(limit=limit)


@admin_router.get(
    "/sponsorship",
    response_model=Page[SponsorshipOptionAdminRead],
)
async def list_admin_sponsorship(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    status_filter: Annotated[str | None, Query(alias="status", max_length=24)] = None,
) -> Page[SponsorshipOptionAdminRead]:
    return await _admin_service(request).list_sponsorship(
        limit=limit,
        offset=offset,
        search=search,
        status=status_filter,
    )


@admin_router.post(
    "/sponsorship",
    response_model=SponsorshipOptionAdminRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_sponsorship_option(
    payload: SponsorshipOptionCreate,
    request: Request,
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> SponsorshipOptionAdminRead:
    del current
    return await _admin_service(request).create_sponsorship(payload)


@admin_router.patch(
    "/sponsorship/{option_id}",
    response_model=SponsorshipOptionAdminRead,
)
async def update_sponsorship_option(
    option_id: str,
    payload: SponsorshipOptionUpdate,
    request: Request,
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> SponsorshipOptionAdminRead:
    del current
    return await _admin_service(request).update_sponsorship(option_id, payload)


@admin_router.delete(
    "/sponsorship/{option_id}",
    response_model=SponsorshipOptionAdminRead,
)
async def archive_sponsorship_option(
    option_id: str,
    request: Request,
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> SponsorshipOptionAdminRead:
    del current
    return await _admin_service(request).archive_sponsorship(option_id)
