"""Request correlation, safe access logs, body limits, and security headers."""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from packages.python.common.errors import RequestTooLargeError
from packages.python.common.request_context import (
    bind_request_id,
    request_id_context,
    reset_request_id,
)

logger = logging.getLogger("portfolio.http")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        supplied_request_id = request.headers.get("X-Request-ID", "")
        request_id = (
            supplied_request_id
            if _REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
            else str(uuid.uuid4())
        )
        token = bind_request_id(request_id)
        started = time.monotonic()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = max(0, int((time.monotonic() - started) * 1000))
            logger.info(
                "http_request_completed",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": response.status_code if response else 500,
                    "duration_ms": duration_ms,
                },
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            reset_request_id(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: object,
        *,
        content_security_policy: str,
        production: bool,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._content_security_policy = content_security_policy
        self._production = production

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", self._content_security_policy)
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
            response.headers.setdefault("Cache-Control", "no-store")
        if self._production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
            )
        return response


class ContentLengthLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        max_bytes: int = 1_048_576,
        route_limits: dict[str, int] | None = None,
    ) -> None:
        self.app = app
        self._max_bytes = max_bytes
        self._route_limits = route_limits or {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path", ""))
        request_limit = min(
            (limit for prefix, limit in self._route_limits.items() if path.startswith(prefix)),
            default=self._max_bytes,
        )
        content_length = Headers(scope=scope).get("content-length")
        if content_length:
            try:
                declared_length = int(content_length)
                too_large = declared_length < 0 or declared_length > request_limit
            except ValueError:
                too_large = True
            if too_large:
                await self._reject(scope, receive, send)
                return

        received_bytes = 0

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > request_limit:
                    raise RequestTooLargeError
            return message

        await self.app(scope, limited_receive, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send) -> None:
        error: dict[str, str] = {
            "code": "request_too_large",
            "message": "Request body is too large",
        }
        request_id = request_id_context.get()
        if request_id:
            error["request_id"] = request_id
        response = JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={"error": error},
        )
        await response(scope, receive, send)
