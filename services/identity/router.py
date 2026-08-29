from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status

from apps.api.auth.dependencies import get_current_admin, get_owner_admin
from apps.api.auth.service import CurrentAdmin
from apps.api.dependencies import get_identity_service
from packages.python.common.errors import NotFoundError
from packages.python.common.http_files import storage_file_response
from packages.python.common.models import PublicationStatus
from packages.python.common.schemas import LifecycleStatusInput, MessageResponse, Page
from services.identity.schemas import (
    PortraitRead,
    PortraitUploadMetadata,
    ProfileCreate,
    ProfileRead,
    ProfileUpdate,
    PublicResumeRead,
    ResumeRead,
    ResumeUploadMetadata,
    SocialLinkCreate,
    SocialLinkRead,
    SocialLinkUpdate,
)
from services.identity.service import IdentityService

public_router = APIRouter(prefix="/api/v1/public", tags=["public-identity"])
admin_router = APIRouter(
    prefix="/api/v1/admin/identity",
    tags=["admin-identity"],
    dependencies=[Depends(get_current_admin)],
)


@public_router.get("/profile", response_model=ProfileRead)
async def public_profile(
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> ProfileRead:
    profile = await service.get_public_profile()
    if profile is None:
        raise NotFoundError("No public profile is available.")
    return profile


@public_router.get("/resume/meta", response_model=PublicResumeRead)
async def public_resume_metadata(
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> PublicResumeRead:
    resume = await service.get_public_current_resume()
    if resume is None:
        raise NotFoundError("No published résumé is currently available.")
    return resume


@public_router.get("/resume")
async def public_resume_download(
    request: Request,
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> Response:
    resume, storage_key = await service.get_public_resume_file()
    return await storage_file_response(
        storage=service.storage,
        key=storage_key,
        size=resume.size_bytes,
        media_type=resume.media_type,
        etag=resume.sha256,
        range_header=request.headers.get("range"),
        cache_control="public, max-age=300, must-revalidate",
        disposition=f'attachment; filename="{resume.download_name}"',
        if_none_match=request.headers.get("if-none-match"),
    )


@public_router.get("/portraits/{portrait_id}")
async def public_portrait(
    portrait_id: UUID,
    request: Request,
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> Response:
    portrait, storage_key = await service.get_public_portrait_file(portrait_id)
    return await storage_file_response(
        storage=service.storage,
        key=storage_key,
        size=portrait.size_bytes,
        media_type=portrait.media_type,
        etag=portrait.sha256,
        range_header=request.headers.get("range"),
        cache_control="public, max-age=86400, immutable",
        if_none_match=request.headers.get("if-none-match"),
    )


@admin_router.get("/profiles", response_model=Page[ProfileRead])
async def list_profiles(
    service: Annotated[IdentityService, Depends(get_identity_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    status_filter: Annotated[PublicationStatus | None, Query(alias="status")] = None,
) -> Page[ProfileRead]:
    return await service.list_profiles(
        limit,
        offset,
        search=search,
        status=status_filter,
    )


@admin_router.post("/profiles", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: ProfileCreate,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> ProfileRead:
    del current
    return await service.create_profile(payload)


@admin_router.get("/profiles/{profile_id}", response_model=ProfileRead)
async def get_profile(
    profile_id: UUID,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> ProfileRead:
    del current
    return await service.get_profile(profile_id)


@admin_router.patch("/profiles/{profile_id}", response_model=ProfileRead)
async def update_profile(
    profile_id: UUID,
    payload: ProfileUpdate,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> ProfileRead:
    del current
    return await service.update_profile(profile_id, payload)


@admin_router.put("/profiles/{profile_id}/status", response_model=ProfileRead)
async def set_profile_status(
    profile_id: UUID,
    payload: LifecycleStatusInput,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> ProfileRead:
    del current
    return await service.set_profile_status(profile_id, payload.status)


@admin_router.post("/portraits", response_model=PortraitRead, status_code=status.HTTP_201_CREATED)
async def upload_portrait(
    service: Annotated[IdentityService, Depends(get_identity_service)],
    profile_id: Annotated[UUID, Form()],
    alt_text: Annotated[str, Form(min_length=1, max_length=300)],
    file: Annotated[UploadFile, File()],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
    width: Annotated[int | None, Form(ge=1, le=50_000)] = None,
    height: Annotated[int | None, Form(ge=1, le=50_000)] = None,
    sort_order: Annotated[int, Form(ge=0, le=10_000)] = 0,
    make_primary: Annotated[bool, Form()] = False,
) -> PortraitRead:
    del current
    metadata = PortraitUploadMetadata(
        profile_id=profile_id,
        alt_text=alt_text,
        width=width,
        height=height,
        sort_order=sort_order,
        make_primary=make_primary,
    )
    content = await file.read(service.settings.max_portrait_bytes + 1)
    return await service.upload_portrait(
        metadata,
        filename=file.filename or "portrait",
        content_type=file.content_type,
        content=content,
    )


@admin_router.put("/portraits/{portrait_id}/primary", response_model=PortraitRead)
async def set_primary_portrait(
    portrait_id: UUID,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> PortraitRead:
    del current
    return await service.set_primary_portrait(portrait_id)


@admin_router.delete("/portraits/{portrait_id}", response_model=PortraitRead)
async def archive_portrait(
    portrait_id: UUID,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> PortraitRead:
    del current
    return await service.archive_portrait(portrait_id)


@admin_router.get("/profiles/{profile_id}/resume-versions", response_model=list[ResumeRead])
async def list_resume_versions(
    profile_id: UUID,
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> list[ResumeRead]:
    return await service.list_resume_versions(profile_id)


@admin_router.post(
    "/resume-versions", response_model=ResumeRead, status_code=status.HTTP_201_CREATED
)
async def upload_resume(
    service: Annotated[IdentityService, Depends(get_identity_service)],
    profile_id: Annotated[UUID, Form()],
    version_label: Annotated[str, Form(min_length=1, max_length=120)],
    file: Annotated[UploadFile, File()],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
    effective_date: Annotated[date | None, Form()] = None,
    download_name: Annotated[str, Form(min_length=1, max_length=255)] = "resume.pdf",
) -> ResumeRead:
    del current
    metadata = ResumeUploadMetadata(
        profile_id=profile_id,
        version_label=version_label,
        effective_date=effective_date,
        download_name=download_name,
    )
    content = await file.read(service.settings.max_resume_bytes + 1)
    return await service.upload_resume(
        metadata,
        filename=file.filename or "resume.pdf",
        content_type=file.content_type,
        content=content,
    )


@admin_router.put("/resume-versions/{resume_id}/publish-current", response_model=ResumeRead)
async def publish_current_resume(
    resume_id: UUID,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> ResumeRead:
    del current
    return await service.publish_and_set_current_resume(resume_id)


@admin_router.delete("/resume-versions/{resume_id}", response_model=ResumeRead)
async def archive_resume(
    resume_id: UUID,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> ResumeRead:
    del current
    return await service.archive_resume(resume_id)


@admin_router.post(
    "/social-links", response_model=SocialLinkRead, status_code=status.HTTP_201_CREATED
)
async def create_social_link(
    payload: SocialLinkCreate,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> SocialLinkRead:
    del current
    return await service.create_social_link(payload)


@admin_router.patch("/social-links/{link_id}", response_model=SocialLinkRead)
async def update_social_link(
    link_id: UUID,
    payload: SocialLinkUpdate,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> SocialLinkRead:
    del current
    return await service.update_social_link(link_id, payload)


@admin_router.delete(
    "/social-links/{link_id}", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def delete_social_link(
    link_id: UUID,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> MessageResponse:
    del current
    await service.delete_social_link(link_id)
    return MessageResponse(message="Social link deleted.")
