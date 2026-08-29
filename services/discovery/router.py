"""HTTP delivery for discovery metadata and crawler surfaces."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Query, Request, Response

from services.discovery.schemas import (
    DiscoveryPageResponse,
    MachineTextResponse,
    SitemapEntryResponse,
)
from services.discovery.service import DiscoveryService

api_router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])
crawler_router = APIRouter(tags=["discovery"])


def _service(request: Request) -> DiscoveryService:
    return cast(DiscoveryService, request.app.state.discovery_service)


@api_router.get("/page", response_model=DiscoveryPageResponse)
async def get_page_discovery(
    request: Request,
    path: str = Query(default="/", min_length=1, max_length=2048),
) -> DiscoveryPageResponse:
    return await _service(request).page(path)


@api_router.get("/sitemap", response_model=list[SitemapEntryResponse])
async def get_sitemap_entries(request: Request) -> list[SitemapEntryResponse]:
    return await _service(request).sitemap_entries()


@api_router.get("/robots", response_model=MachineTextResponse)
async def get_robots_text(request: Request) -> MachineTextResponse:
    return MachineTextResponse(content=await _service(request).robots_txt())


@api_router.get("/llms", response_model=MachineTextResponse)
async def get_llms_text(request: Request) -> MachineTextResponse:
    return MachineTextResponse(content=await _service(request).llms_txt())


@crawler_router.get("/sitemap.xml", include_in_schema=False)
async def sitemap(request: Request) -> Response:
    return Response(
        content=await _service(request).sitemap_xml(),
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=3600"},
    )


@crawler_router.get("/robots.txt", include_in_schema=False)
async def robots(request: Request) -> Response:
    return Response(
        content=await _service(request).robots_txt(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@crawler_router.get("/llms.txt", include_in_schema=False)
async def llms_txt(request: Request) -> Response:
    return Response(
        content=await _service(request).llms_txt(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=3600"},
    )
