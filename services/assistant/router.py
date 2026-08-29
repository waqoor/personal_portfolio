"""FastAPI transport adapter for assistant requests."""

from __future__ import annotations

from fastapi import APIRouter, Request

from services.assistant.schemas import AssistantAnswer, AssistantQuestion
from services.assistant.service import AssistantService

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


@router.post("/query", response_model=AssistantAnswer)
async def query_assistant(payload: AssistantQuestion, request: Request) -> AssistantAnswer:
    service: AssistantService = request.app.state.assistant_service
    client_ip = request.client.host if request.client else "unknown"
    return await service.answer(payload, client_ip=client_ip)
