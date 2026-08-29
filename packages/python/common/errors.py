"""Stable application errors mapped at the API boundary."""

from __future__ import annotations


class ApplicationError(RuntimeError):
    code = "application_error"

    def __init__(self, public_message: str = "The request could not be completed") -> None:
        super().__init__(public_message)
        self.public_message = public_message


class ValidationError(ApplicationError):
    code = "validation_error"


class ConflictError(ApplicationError):
    code = "conflict"


class UnauthorizedError(ApplicationError):
    code = "unauthorized"

    def __init__(self, public_message: str = "Authentication is required.") -> None:
        super().__init__(public_message)


class ForbiddenError(ApplicationError):
    code = "forbidden"


class RateLimitError(ApplicationError):
    code = "rate_limited"

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Too many requests. Please try again later.")
        self.retry_after_seconds = retry_after_seconds


class StorageError(ApplicationError):
    code = "storage_error"

    def __init__(self, public_message: str = "Managed storage is unavailable.") -> None:
        super().__init__(public_message)


class FeatureUnavailableError(ApplicationError):
    code = "feature_unavailable"


class RateLimitExceededError(RateLimitError):
    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__(retry_after_seconds)


class UnsafeInputError(ApplicationError):
    code = "unsafe_input"


class RequestTooLargeError(ApplicationError):
    code = "request_too_large"

    def __init__(self) -> None:
        super().__init__("Request body is too large")


class NotFoundError(ApplicationError):
    code = "not_found"
