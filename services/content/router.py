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
from apps.api.auth.service import CurrentAdmin
from apps.api.dependencies import get_content_service, get_homepage_composer
from packages.python.common.http_files import storage_file_response
from packages.python.common.models import PublicationStatus
from packages.python.common.schemas import LifecycleStatusInput, Page
from services.content.schemas import (
    ArticleCreate,
    ArticlePage,
    ArticleRead,
    ArticleUpdate,
    FeatureSettingRead,
    FeatureSettingUpsert,
    HomepageCompositionUpdate,
    HomepageRead,
    HomepageSectionCreate,
    HomepageSectionRead,
    HomepageSectionUpdate,
    MediaRead,
    MediaUpdate,
    MediaUploadMetadata,
    NavigationItemCreate,
    NavigationItemRead,
    NavigationItemUpdate,
    PublicArticleRead,
    PublicSiteShellRead,
    SitePresentationSettings,
)
from services.content.service import ContentService, HomepageComposer

public_router = APIRouter(prefix="/api/v1/public", tags=["public-content"])
admin_router = APIRouter(
    prefix="/api/v1/admin/content",
    tags=["admin-content"],
    dependencies=[Depends(get_current_admin)],
)


@public_router.get("/homepage", response_model=HomepageRead)
async def homepage(
    composer: Annotated[HomepageComposer, Depends(get_homepage_composer)],
) -> HomepageRead:
    return await composer.compose()


@public_router.get("/site-shell", response_model=PublicSiteShellRead)
async def site_shell(
    composer: Annotated[HomepageComposer, Depends(get_homepage_composer)],
) -> PublicSiteShellRead:
    return await composer.compose_site_shell()


@public_router.get("/navigation", response_model=list[NavigationItemRead])
async def navigation(
    service: Annotated[ContentService, Depends(get_content_service)],
) -> list[NavigationItemRead]:
    return await service.list_public_navigation()


@public_router.get("/site-presentation", response_model=SitePresentationSettings)
async def site_presentation(
    service: Annotated[ContentService, Depends(get_content_service)],
) -> SitePresentationSettings:
    return await service.get_site_presentation()


@public_router.get("/articles", response_model=ArticlePage)
async def articles(
    service: Annotated[ContentService, Depends(get_content_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    topic: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> ArticlePage:
    return await service.list_public_articles_page(
        limit=limit,
        offset=offset,
        topic=topic,
        search=search,
    )


@public_router.get("/articles/{slug}", response_model=PublicArticleRead)
async def article(
    slug: str,
    service: Annotated[ContentService, Depends(get_content_service)],
) -> PublicArticleRead:
    return await service.get_public_article(slug)


@public_router.get("/media/{media_id}")
async def public_media(
    media_id: UUID,
    request: Request,
    service: Annotated[ContentService, Depends(get_content_service)],
) -> Response:
    media, storage_key = await service.get_public_media_file(media_id)
    return await storage_file_response(
        storage=service.storage,
        key=storage_key,
        size=media.size_bytes,
        media_type=media.media_type,
        etag=media.sha256,
        range_header=request.headers.get("range"),
        cache_control="public, max-age=86400, immutable",
        if_none_match=request.headers.get("if-none-match"),
    )


def _list_route(resource: str, response_model: type[Any]) -> None:
    async def route(
        service: Annotated[ContentService, Depends(get_content_service)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
        status_filter: Annotated[PublicationStatus | None, Query(alias="status")] = None,
    ) -> Page[Any]:
        return await service.list_admin(
            resource,
            limit,
            offset,
            search=search,
            status=status_filter,
        )

    route.__name__ = f"list_admin_content_{resource}"
    admin_router.add_api_route(
        f"/{resource}",
        route,
        methods=["GET"],
        response_model=Page[response_model],  # type: ignore[valid-type]
    )


for _resource, _schema in (
    ("media", MediaRead),
    ("articles", ArticleRead),
    ("sections", HomepageSectionRead),
    ("navigation", NavigationItemRead),
    ("features", FeatureSettingRead),
):
    _list_route(_resource, _schema)


@admin_router.post("/media", response_model=MediaRead, status_code=status.HTTP_201_CREATED)
async def upload_media(
    service: Annotated[ContentService, Depends(get_content_service)],
    file: Annotated[UploadFile, File()],
    alt_text: Annotated[str, Form(max_length=300)] = "",
    is_decorative: Annotated[bool, Form()] = False,
    caption: Annotated[str | None, Form(max_length=500)] = None,
    width: Annotated[int | None, Form(ge=1, le=50_000)] = None,
    height: Annotated[int | None, Form(ge=1, le=50_000)] = None,
    duration_seconds: Annotated[int | None, Form(ge=0, le=604_800)] = None,
) -> MediaRead:
    metadata = MediaUploadMetadata(
        alt_text=alt_text,
        is_decorative=is_decorative,
        caption=caption,
        width=width,
        height=height,
        duration_seconds=duration_seconds,
    )
    content = await file.read(service.settings.max_media_bytes + 1)
    return await service.upload_media(
        metadata,
        filename=file.filename or "media",
        content_type=file.content_type,
        content=content,
    )


@admin_router.patch("/media/{media_id}", response_model=MediaRead)
async def update_media(
    media_id: UUID,
    payload: MediaUpdate,
    service: Annotated[ContentService, Depends(get_content_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> MediaRead:
    require_owner_for_publication_fields(current, payload.model_fields_set)
    return await service.update_media(media_id, payload)


@admin_router.post("/articles", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
async def create_article(
    payload: ArticleCreate,
    service: Annotated[ContentService, Depends(get_content_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> ArticleRead:
    require_owner_for_initial_status(current, payload.status)
    return await service.create_article(payload)


@admin_router.patch("/articles/{article_id}", response_model=ArticleRead)
async def update_article(
    article_id: UUID,
    payload: ArticleUpdate,
    service: Annotated[ContentService, Depends(get_content_service)],
    current: Annotated[CurrentAdmin, Depends(get_current_admin)],
) -> ArticleRead:
    require_owner_for_publication_fields(current, payload.model_fields_set)
    return await service.update_article(article_id, payload)


@admin_router.post(
    "/sections", response_model=HomepageSectionRead, status_code=status.HTTP_201_CREATED
)
async def create_section(
    payload: HomepageSectionCreate,
    service: Annotated[ContentService, Depends(get_content_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> HomepageSectionRead:
    del current
    return await service.create_section(payload)


@admin_router.patch("/sections/{section_id}", response_model=HomepageSectionRead)
async def update_section(
    section_id: UUID,
    payload: HomepageSectionUpdate,
    service: Annotated[ContentService, Depends(get_content_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> HomepageSectionRead:
    del current
    return await service.update_section(section_id, payload)


@admin_router.put("/sections/composition", response_model=list[HomepageSectionRead])
async def replace_homepage_composition(
    payload: HomepageCompositionUpdate,
    service: Annotated[ContentService, Depends(get_content_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> list[HomepageSectionRead]:
    del current
    return await service.replace_homepage_composition(payload)


@admin_router.post(
    "/navigation", response_model=NavigationItemRead, status_code=status.HTTP_201_CREATED
)
async def create_navigation(
    payload: NavigationItemCreate,
    service: Annotated[ContentService, Depends(get_content_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> NavigationItemRead:
    del current
    return await service.create_navigation(payload)


@admin_router.patch("/navigation/{item_id}", response_model=NavigationItemRead)
async def update_navigation(
    item_id: UUID,
    payload: NavigationItemUpdate,
    service: Annotated[ContentService, Depends(get_content_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> NavigationItemRead:
    del current
    return await service.update_navigation(item_id, payload)


@admin_router.put("/features", response_model=FeatureSettingRead)
async def upsert_feature(
    payload: FeatureSettingUpsert,
    service: Annotated[ContentService, Depends(get_content_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> FeatureSettingRead:
    del current
    return await service.upsert_feature(payload)


@admin_router.delete("/features/{feature_id}", response_model=FeatureSettingRead)
async def archive_feature(
    feature_id: UUID,
    service: Annotated[ContentService, Depends(get_content_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> FeatureSettingRead:
    del current
    return await service.archive_feature(feature_id)


@admin_router.put("/{resource}/{entity_id}/status", response_model=Any)
async def set_content_status(
    resource: str,
    entity_id: UUID,
    payload: LifecycleStatusInput,
    service: Annotated[ContentService, Depends(get_content_service)],
    current: Annotated[CurrentAdmin, Depends(get_owner_admin)],
) -> Any:
    del current
    return await service.set_status(resource, entity_id, payload.status)
