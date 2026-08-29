"""Consistent public error envelopes with privacy-safe validation details."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from packages.python.common.errors import (
    ApplicationError,
    ConflictError,
    FeatureUnavailableError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    RateLimitExceededError,
    RequestTooLargeError,
    StorageError,
    UnauthorizedError,
    UnsafeInputError,
    ValidationError,
)
from packages.python.common.request_context import request_id_context

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        del request
        response_status = status.HTTP_400_BAD_REQUEST
        headers: dict[str, str] = {}
        if isinstance(exc, (RateLimitExceededError, RateLimitError)):
            response_status = status.HTTP_429_TOO_MANY_REQUESTS
            headers["Retry-After"] = str(exc.retry_after_seconds)
        elif isinstance(exc, FeatureUnavailableError):
            response_status = status.HTTP_503_SERVICE_UNAVAILABLE
            headers["Retry-After"] = "60"
        elif isinstance(exc, NotFoundError):
            response_status = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, UnauthorizedError):
            response_status = status.HTTP_401_UNAUTHORIZED
            headers["WWW-Authenticate"] = "Session"
        elif isinstance(exc, ForbiddenError):
            response_status = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, ConflictError):
            response_status = status.HTTP_409_CONFLICT
        elif isinstance(exc, RequestTooLargeError):
            response_status = status.HTTP_413_CONTENT_TOO_LARGE
        elif isinstance(exc, (UnsafeInputError, ValidationError)):
            response_status = status.HTTP_422_UNPROCESSABLE_CONTENT
        elif isinstance(exc, StorageError):
            response_status = status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(
            status_code=response_status,
            headers=headers,
            content=_error_content(exc.code, exc.public_message),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        del request
        details = [
            {
                "location": [str(part) for part in error.get("loc", ())],
                "type": str(error.get("type", "validation_error")),
                "message": str(error.get("msg", "Invalid value")),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                **_error_content("validation_error", "Request validation failed"),
                "details": details,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        del request
        validation_errors = (
            [
                {
                    "location": [str(part) for part in error.get("loc", ())],
                    "type": str(error.get("type", "validation_error")),
                }
                for error in exc.errors()
            ]
            if isinstance(exc, PydanticValidationError)
            else None
        )
        logger.error(
            "unhandled_application_error",
            extra={
                "error_type": type(exc).__name__,
                "validation_errors": validation_errors,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_content("internal_error", "An unexpected error occurred"),
        )


def _error_content(code: str, message: str) -> dict[str, object]:
    request_id = request_id_context.get()
    error: dict[str, object] = {"code": code, "message": message}
    if request_id:
        error["request_id"] = request_id
    return {"error": error}
