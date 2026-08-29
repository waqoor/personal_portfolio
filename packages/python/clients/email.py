"""Provider-neutral email boundary used by business services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class EmailClientError(RuntimeError):
    """Normalized email-client failure safe to handle outside the adapter."""


class EmailProviderUnavailable(EmailClientError):
    """The configured provider could not accept the message."""


@dataclass(frozen=True, slots=True)
class ContactNotification:
    submission_id: str
    delivery_key: str
    sender_name: str
    sender_email: str
    category: str
    subject: str | None
    message: str
    submitted_at_iso: str
    organization: str | None = None


@dataclass(frozen=True, slots=True)
class SystemEmail:
    recipient: str
    subject: str
    plain_text: str


@dataclass(frozen=True, slots=True)
class EmailDeliveryResult:
    provider_message_id: str | None = None


@runtime_checkable
class EmailClient(Protocol):
    async def send_contact_notification(
        self, notification: ContactNotification
    ) -> EmailDeliveryResult: ...

    async def send_system_email(self, message: SystemEmail) -> EmailDeliveryResult: ...

    async def health_check(self) -> bool: ...

    async def close(self) -> None: ...
