from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status

from apps.api.auth.dependencies import (
    get_current_admin,
    get_owner_admin,
    require_owner_for_initial_status,
    require_owner_for_publication_fields,
)
from apps.api.auth.service import AuthService, CurrentAdmin
from apps.api.dependencies import get_portfolio_service
from packages.python.common.http_files import storage_file_response
from packages.python.common.models import PublicationStatus
from packages.python.common.schemas import LifecycleStatusInput, Page
from services.portfolio.schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    CertificationCreate,
    CertificationRead,
    CertificationUpdate,
    EducationCreate,
    EducationRead,
    EducationUpdate,
    ExperienceCreate,
    ExperienceRead,
    ExperienceUpdate,
    FeaturedProjectOrderRead,
    FeaturedProjectOrderUpdate,
    MetricCreate,
    MetricRead,
    MetricUpdate,
    ProjectCreate,
    ProjectMediaCreate,
    ProjectMediaRead,
    ProjectMediaUpdate,
    ProjectMediaUploadMetadata,
    ProjectRead,
    ProjectUpdate,
    PublicMetricRead,
    PublicProjectRead,
    PublicProjectSummaryRead,
    PublicSectorDetailRead,
    PublicSkillRead,
    PublicTestimonialRead,
    RepositoryMetadataAdminRead,
    SectorCreate,
    SectorRead,
    SectorUpdate,
    SkillCreate,
    SkillRead,
    SkillUpdate,
    TestimonialCreate,
    TestimonialRead,
    TestimonialUpdate,
)
from services.portfolio.service import PortfolioService

public_router = APIRouter(prefix="/api/v1/public", tags=["public-portfolio"])
admin_router = APIRouter(
    prefix="/api/v1/admin/portfolio",
    tags=["admin-portfolio"],
    dependencies=[Depends(get_current_admin)],
)


@public_router.get("/categories", response_model=list[CategoryRead])
async def public_categories(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[CategoryRead]:
    return await service.list_public_categories(limit)


@public_router.get("/sectors", response_model=list[SectorRead])
async def public_sectors(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[SectorRead]:
    return await service.list_public_sectors(limit)


@public_router.get("/sectors/{slug}", response_model=PublicSectorDetailRead)
async def public_sector(
    slug: str,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> PublicSectorDetailRead:
    return await service.get_public_sector(slug)


@public_router.get("/skills", response_model=list[PublicSkillRead])
async def public_skills(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[PublicSkillRead]:
    return await service.list_public_skills(limit)


@public_router.get("/experiences", response_model=list[ExperienceRead])
async def public_experiences(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ExperienceRead]:
    return await service.list_public_experiences(limit)


@public_router.get("/education", response_model=list[EducationRead])
async def public_education(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[EducationRead]:
    return await service.list_public_education(limit)


@public_router.get("/certifications", response_model=list[CertificationRead])
async def public_certifications(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[CertificationRead]:
    return await service.list_public_certifications(limit)


@public_router.get("/projects", response_model=Page[PublicProjectSummaryRead])
async def public_projects(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    category: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    sector: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    open_source: bool | None = None,
) -> Page[PublicProjectSummaryRead]:
    return await service.list_public_projects_page(
        limit=limit,
        offset=offset,
        category=category,
        sector=sector,
        search=search,
        open_source=open_source,
    )


@public_router.get("/projects/{slug}", response_model=PublicProjectRead)
async def public_project(
    slug: str,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> PublicProjectRead:
    return await service.get_public_project(slug)


@public_router.get("/project-media/{media_id}")
async def public_project_media(
    media_id: UUID,
    request: Request,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> Response:
    media, storage_key = await service.get_public_project_media_file(media_id)
    return await storage_file_response(
        storage=service.storage,
        key=storage_key,
        size=media.size_bytes or 0,
        media_type=media.media_type,
        etag=media.sha256 or "",
        range_header=request.headers.get("range"),
        cache_control="public, max-age=86400, immutable",
        if_none_match=request.headers.get("if-none-match"),
    )


@public_router.get("/metrics", response_model=list[PublicMetricRead])
async def public_metrics(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[PublicMetricRead]:
    return await service.list_public_metrics(limit)


@public_router.get("/testimonials", response_model=list[PublicTestimonialRead])
async def public_testimonials(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[PublicTestimonialRead]:
    return await service.list_public_testimonials(limit)


def _list_route(resource: str, response_model: type[Any]) -> Any:
    async def route(
        service: Annotated[PortfolioService, Depends(get_portfolio_service)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
        status_filter: Annotated[PublicationStatus | None, Query(alias="status")] = None,
        open_source: bool | None = None,
        approved: bool | None = None,
    ) -> Page[Any]:
        return await service.list_admin(
            resource,
            limit,
            offset,
            search=search,
            status=status_filter,
            open_source=open_source,
            approved=approved,
        )

    route.__name__ = f"list_admin_{resource}"
    admin_router.add_api_route(
        f"/{resource}",
        route,
        methods=["GET"],
        response_model=Page[response_model],  # type: ignore[valid-type]
    )
    return route


for _resource, _schema in (
    ("categories", CategoryRead),
    ("sectors", SectorRead),
    ("skills", SkillRead),
    ("experiences", ExperienceRead),
    ("education", EducationRead),
    ("certifications", CertificationRead),
    ("projects", ProjectRead),
    ("metrics", MetricRead),
    ("testimonials", TestimonialRead),
):
    _list_route(_resource, _schema)


@admin_router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> CategoryRead:
    require_owner_for_initial_status(current, payload.status)
    return await service.create_category(payload)


@admin_router.patch("/categories/{entity_id}", response_model=CategoryRead)
async def update_category(
    entity_id: UUID,
    payload: CategoryUpdate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> CategoryRead:
    require_owner_for_publication_fields(current, payload.model_fields_set)
    return await service.update_category(entity_id, payload)


@admin_router.post("/sectors", response_model=SectorRead, status_code=status.HTTP_201_CREATED)
async def create_sector(
    payload: SectorCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> SectorRead:
    require_owner_for_initial_status(current, payload.status)
    return await service.create_sector(payload)


@admin_router.patch("/sectors/{entity_id}", response_model=SectorRead)
async def update_sector(
    entity_id: UUID,
    payload: SectorUpdate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> SectorRead:
    require_owner_for_publication_fields(current, payload.model_fields_set)
    return await service.update_sector(entity_id, payload)


@admin_router.post("/skills", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def create_skill(
    payload: SkillCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> SkillRead:
    require_owner_for_initial_status(current, payload.status)
    return await service.create_skill(payload)


@admin_router.patch("/skills/{entity_id}", response_model=SkillRead)
async def update_skill(
    entity_id: UUID,
    payload: SkillUpdate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> SkillRead:
    require_owner_for_publication_fields(current, payload.model_fields_set)
    return await service.update_skill(entity_id, payload)


@admin_router.post(
    "/experiences", response_model=ExperienceRead, status_code=status.HTTP_201_CREATED
)
async def create_experience(
    payload: ExperienceCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> ExperienceRead:
    require_owner_for_initial_status(current, payload.status)
    return await service.create_experience(payload)


@admin_router.patch("/experiences/{entity_id}", response_model=ExperienceRead)
async def update_experience(
    entity_id: UUID,
    payload: ExperienceUpdate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> ExperienceRead:
    require_owner_for_publication_fields(current, payload.model_fields_set)
    return await service.update_experience(entity_id, payload)


@admin_router.post("/education", response_model=EducationRead, status_code=status.HTTP_201_CREATED)
async def create_education(
    payload: EducationCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> EducationRead:
    require_owner_for_initial_status(current, payload.status)
    return await service.create_education(payload)


@admin_router.patch("/education/{entity_id}", response_model=EducationRead)
async def update_education(
    entity_id: UUID,
    payload: EducationUpdate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> EducationRead:
    require_owner_for_publication_fields(current, payload.model_fields_set)
    return await service.update_education(entity_id, payload)


@admin_router.post(
    "/certifications", response_model=CertificationRead, status_code=status.HTTP_201_CREATED
)
async def create_certification(
    payload: CertificationCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> CertificationRead:
    require_owner_for_initial_status(current, payload.status)
    return await service.create_certification(payload)


@admin_router.patch("/certifications/{entity_id}", response_model=CertificationRead)
async def update_certification(
    entity_id: UUID,
    payload: CertificationUpdate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> CertificationRead:
    require_owner_for_publication_fields(current, payload.model_fields_set)
    return await service.update_certification(entity_id, payload)


@admin_router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> ProjectRead:
    require_owner_for_initial_status(current, payload.status)
    return await service.create_project(payload)


@admin_router.put("/projects/featured-order", response_model=list[ProjectRead])
async def replace_featured_order(
    payload: FeaturedProjectOrderUpdate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> list[ProjectRead]:
    del current
    return await service.replace_featured_order(payload)


@admin_router.get("/projects/featured-order", response_model=FeaturedProjectOrderRead)
async def get_featured_order(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> FeaturedProjectOrderRead:
    del current
    return await service.get_featured_order()


@admin_router.post(
    "/projects/{entity_id}/repository-metadata/refresh",
    response_model=RepositoryMetadataAdminRead,
)
async def refresh_repository_metadata(
    entity_id: UUID,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
    force: Annotated[bool, Query()] = False,
) -> RepositoryMetadataAdminRead:
    del current
    return await service.refresh_repository_metadata(entity_id, force=force)


@admin_router.get("/projects/{entity_id}", response_model=ProjectRead)
async def get_project(
    entity_id: UUID,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> ProjectRead:
    return await service.get_project(entity_id)


@admin_router.patch("/projects/{entity_id}", response_model=ProjectRead)
async def update_project(
    entity_id: UUID,
    payload: ProjectUpdate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> ProjectRead:
    require_owner_for_publication_fields(
        current,
        payload.model_fields_set,
        extra_fields={"featured_rank", "repository_metadata_refresh_enabled"},
    )
    return await service.update_project(entity_id, payload)


@admin_router.post(
    "/project-media", response_model=ProjectMediaRead, status_code=status.HTTP_201_CREATED
)
async def create_project_media(
    payload: ProjectMediaCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> ProjectMediaRead:
    if payload.is_visible:
        AuthService.require_owner(current)
    return await service.create_project_media(payload)


@admin_router.get("/project-media", response_model=Page[ProjectMediaRead])
async def list_project_media(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> Page[ProjectMediaRead]:
    return await service.list_project_media(limit, offset, search=search)


@admin_router.post(
    "/project-media/upload",
    response_model=ProjectMediaRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_project_media(
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
    project_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    alt_text: Annotated[str, Form(max_length=300)] = "",
    is_decorative: Annotated[bool, Form()] = False,
    caption: Annotated[str | None, Form(max_length=500)] = None,
    width: Annotated[int | None, Form(ge=1, le=50_000)] = None,
    height: Annotated[int | None, Form(ge=1, le=50_000)] = None,
    duration_seconds: Annotated[int | None, Form(ge=0, le=604_800)] = None,
    sort_order: Annotated[int, Form(ge=0, le=100_000)] = 0,
    is_visible: Annotated[bool, Form()] = True,
) -> ProjectMediaRead:
    if is_visible:
        AuthService.require_owner(current)
    metadata = ProjectMediaUploadMetadata(
        project_id=project_id,
        alt_text=alt_text,
        is_decorative=is_decorative,
        caption=caption,
        width=width,
        height=height,
        duration_seconds=duration_seconds,
        sort_order=sort_order,
        is_visible=is_visible,
    )
    content = await file.read(service.settings.max_media_bytes + 1)
    return await service.upload_project_media(
        metadata,
        filename=file.filename or "project-media",
        content_type=file.content_type,
        content=content,
    )


@admin_router.delete("/project-media/{media_id}", response_model=ProjectMediaRead)
async def archive_project_media(
    media_id: UUID,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> ProjectMediaRead:
    del current
    return await service.archive_project_media(media_id)


@admin_router.patch("/project-media/{media_id}", response_model=ProjectMediaRead)
async def update_project_media(
    media_id: UUID,
    payload: ProjectMediaUpdate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> ProjectMediaRead:
    require_owner_for_publication_fields(
        current,
        payload.model_fields_set,
        extra_fields={"project_id", "external_url", "media_type"},
    )
    return await service.update_project_media(media_id, payload)


@admin_router.post("/metrics", response_model=MetricRead, status_code=status.HTTP_201_CREATED)
async def create_metric(
    payload: MetricCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> MetricRead:
    require_owner_for_initial_status(current, payload.status)
    return await service.create_metric(payload, current.user.id)


@admin_router.patch("/metrics/{entity_id}", response_model=MetricRead)
async def update_metric(
    entity_id: UUID,
    payload: MetricUpdate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> MetricRead:
    require_owner_for_publication_fields(current, payload.model_fields_set)
    return await service.update_metric(entity_id, payload, current.user.id)


@admin_router.put("/metrics/{entity_id}/approval", response_model=MetricRead)
async def approve_metric(
    entity_id: UUID,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> MetricRead:
    return await service.approve_metric(entity_id, current.user.id)


@admin_router.delete("/metrics/{entity_id}/approval", response_model=MetricRead)
async def revoke_metric_approval(
    entity_id: UUID,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> MetricRead:
    return await service.revoke_metric_approval(entity_id, current.user.id)


@admin_router.post(
    "/testimonials", response_model=TestimonialRead, status_code=status.HTTP_201_CREATED
)
async def create_testimonial(
    payload: TestimonialCreate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> TestimonialRead:
    require_owner_for_initial_status(current, payload.status)
    return await service.create_testimonial(payload, current.user.id)


@admin_router.patch("/testimonials/{entity_id}", response_model=TestimonialRead)
async def update_testimonial(
    entity_id: UUID,
    payload: TestimonialUpdate,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> TestimonialRead:
    require_owner_for_publication_fields(current, payload.model_fields_set)
    return await service.update_testimonial(entity_id, payload, current.user.id)


@admin_router.put("/testimonials/{entity_id}/approval", response_model=TestimonialRead)
async def approve_testimonial(
    entity_id: UUID,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> TestimonialRead:
    return await service.approve_testimonial(entity_id, current.user.id)


@admin_router.delete("/testimonials/{entity_id}/approval", response_model=TestimonialRead)
async def revoke_testimonial_approval(
    entity_id: UUID,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> TestimonialRead:
    return await service.revoke_testimonial_approval(entity_id, current.user.id)


@admin_router.put("/{resource}/{entity_id}/status", response_model=Any)
async def set_resource_status(
    resource: str,
    entity_id: UUID,
    payload: LifecycleStatusInput,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> Any:
    del current
    return await service.set_status(resource, entity_id, payload.status)
