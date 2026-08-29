"""External infrastructure client contracts and production adapters."""

from packages.python.clients.ai import (
    AIGenerationRequest,
    AIMessage,
    AIProviderClient,
    AIProviderError,
    AIProviderResponse,
    AIProviderUnavailable,
)
from packages.python.clients.database import DatabaseClient
from packages.python.clients.email import (
    ContactNotification,
    EmailClient,
    EmailClientError,
    EmailDeliveryResult,
    EmailProviderUnavailable,
    SystemEmail,
)
from packages.python.common.models import Base

__all__ = [
    "AIGenerationRequest",
    "AIMessage",
    "AIProviderClient",
    "AIProviderError",
    "AIProviderResponse",
    "AIProviderUnavailable",
    "Base",
    "ContactNotification",
    "DatabaseClient",
    "EmailClient",
    "EmailClientError",
    "EmailDeliveryResult",
    "EmailProviderUnavailable",
    "SystemEmail",
]
