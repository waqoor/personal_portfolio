"""Production SMTP implementation of the EmailClient boundary."""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid

from packages.python.clients.email import (
    ContactNotification,
    EmailDeliveryResult,
    EmailProviderUnavailable,
    SystemEmail,
)


def _safe_header(value: str) -> str:
    if "\r" in value or "\n" in value:
        raise ValueError("Email header values cannot contain line breaks")
    return value


class SMTPEmailClient:
    """Blocking SMTP is isolated behind an async adapter and strict timeout."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        from_address: str,
        contact_recipient: str,
        username: str | None = None,
        password: str | None = None,
        use_starttls: bool = True,
        use_ssl: bool = False,
        timeout_seconds: float = 8.0,
    ) -> None:
        if use_starttls and use_ssl:
            raise ValueError("SMTP STARTTLS and implicit TLS cannot both be enabled")
        self._host = host
        self._port = port
        self._from_address = _safe_header(from_address)
        self._contact_recipient = _safe_header(contact_recipient)
        self._username = username
        self._password = password
        self._use_starttls = use_starttls
        self._use_ssl = use_ssl
        self._timeout_seconds = timeout_seconds

    async def send_contact_notification(
        self, notification: ContactNotification
    ) -> EmailDeliveryResult:
        subject_suffix = notification.subject or notification.category
        message = EmailMessage()
        message["Subject"] = _safe_header(f"Portfolio contact: {subject_suffix}")
        message["From"] = self._from_address
        message["To"] = self._contact_recipient
        message["Reply-To"] = _safe_header(notification.sender_email)
        provider_id = make_msgid(domain=self._from_address.rpartition("@")[2] or None)
        message["Message-ID"] = provider_id
        lines = [
            f"Submission: {notification.submission_id}",
            f"Received: {notification.submitted_at_iso}",
            f"Name: {notification.sender_name}",
            f"Email: {notification.sender_email}",
            f"Category: {notification.category}",
        ]
        if notification.organization:
            lines.append(f"Organization: {notification.organization}")
        lines.extend(("", notification.message))
        message.set_content("\n".join(lines))
        await self._send(message)
        return EmailDeliveryResult(provider_message_id=provider_id.strip("<>"))

    async def send_system_email(self, message: SystemEmail) -> EmailDeliveryResult:
        email_message = EmailMessage()
        email_message["Subject"] = _safe_header(message.subject)
        email_message["From"] = self._from_address
        email_message["To"] = _safe_header(message.recipient)
        provider_id = make_msgid(domain=self._from_address.rpartition("@")[2] or None)
        email_message["Message-ID"] = provider_id
        email_message.set_content(message.plain_text)
        await self._send(email_message)
        return EmailDeliveryResult(provider_message_id=provider_id.strip("<>"))

    async def _send(self, message: EmailMessage) -> None:
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._send_sync, message),
                timeout=self._timeout_seconds + 1,
            )
        except (TimeoutError, OSError, smtplib.SMTPException) as exc:
            raise EmailProviderUnavailable("The email provider is unavailable") from exc

    def _send_sync(self, message: EmailMessage) -> None:
        context = ssl.create_default_context()
        smtp_type = smtplib.SMTP_SSL if self._use_ssl else smtplib.SMTP
        smtp_kwargs: dict[str, object] = {
            "host": self._host,
            "port": self._port,
            "timeout": self._timeout_seconds,
        }
        if self._use_ssl:
            smtp_kwargs["context"] = context
        with smtp_type(**smtp_kwargs) as connection:  # type: ignore[arg-type]
            connection.ehlo()
            if self._use_starttls:
                connection.starttls(context=context)
                connection.ehlo()
            if self._username:
                connection.login(self._username, self._password or "")
            connection.send_message(message)

    async def health_check(self) -> bool:
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self._health_check_sync),
                timeout=self._timeout_seconds + 1,
            )
        except (TimeoutError, OSError, smtplib.SMTPException):
            return False
        return True

    def _health_check_sync(self) -> None:
        context = ssl.create_default_context()
        smtp_type = smtplib.SMTP_SSL if self._use_ssl else smtplib.SMTP
        smtp_kwargs: dict[str, object] = {
            "host": self._host,
            "port": self._port,
            "timeout": self._timeout_seconds,
        }
        if self._use_ssl:
            smtp_kwargs["context"] = context
        with smtp_type(**smtp_kwargs) as connection:  # type: ignore[arg-type]
            connection.ehlo()
            if self._use_starttls:
                connection.starttls(context=context)
                connection.ehlo()
            if self._username:
                connection.login(self._username, self._password or "")

    async def close(self) -> None:
        """SMTP connections are intentionally short-lived per delivery."""
