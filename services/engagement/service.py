"""Contact and sponsorship business behavior."""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from packages.python.clients.email import ContactNotification, EmailClient
from packages.python.common.errors import (
    ConflictError,
    FeatureUnavailableError,
    NotFoundError,
    RateLimitExceededError,
    UnsafeInputError,
)
from packages.python.common.privacy import hmac_fingerprint
from packages.python.common.rate_limit import DatabaseRateLimiter, RateLimitRequest
from packages.python.common.schemas import Page
from packages.python.contracts.features import FeatureFlagReader
from services.engagement.contracts import (
    EngagementAdminRepository,
    EngagementRepository,
    NewContactSubmission,
)
from services.engagement.schemas import (
    ContactCategoryOption,
    ContactNotificationBatchResult,
    ContactOptionsResponse,
    ContactReceipt,
    ContactRequest,
    ContactStatusUpdate,
    ContactSubmissionAdminRead,
    SponsorshipOptionAdminRead,
    SponsorshipOptionCreate,
    SponsorshipOptionResponse,
    SponsorshipOptionsResponse,
    SponsorshipOptionUpdate,
    is_github_sponsors_destination,
)

logger = logging.getLogger(__name__)
_LINK_PATTERN = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ContactServiceConfig:
    enabled: bool
    email_enabled: bool
    privacy_hash_secret: str
    rate_limit_window_seconds: int
    ip_limit: int
    email_limit: int
    max_links: int
    response_time_label: str = "Usually within 2-3 business days."


@dataclass(frozen=True, slots=True)
class ContactRequestContext:
    client_ip: str
    idempotency_key: str | None = None


class ContactService:
    def __init__(
        self,
        *,
        repository: EngagementRepository,
        email_client: EmailClient | None,
        rate_limiter: DatabaseRateLimiter,
        config: ContactServiceConfig,
        feature_flags: FeatureFlagReader | None = None,
    ) -> None:
        self._repository = repository
        self._email_client = email_client
        self._rate_limiter = rate_limiter
        self._config = config
        self._feature_flags = feature_flags

    async def submit(
        self, request: ContactRequest, context: ContactRequestContext
    ) -> ContactReceipt:
        enabled = await self._is_enabled()
        if not enabled:
            raise FeatureUnavailableError("Contact is currently unavailable")
        now = datetime.now(UTC)
        if request.website:
            logger.info("contact_honeypot_rejected")
            return ContactReceipt(reference_id=str(uuid.uuid4()), accepted_at=now)
        if len(_LINK_PATTERN.findall(request.message)) > self._config.max_links:
            raise UnsafeInputError("Message contains too many links")

        normalized_email = str(request.email).strip().casefold()
        ip_hash = hmac_fingerprint(
            self._config.privacy_hash_secret,
            context.client_ip or "unknown",
            namespace="contact-ip",
        )
        email_hash = hmac_fingerprint(
            self._config.privacy_hash_secret,
            normalized_email,
            namespace="contact-email",
        )
        idempotency_hash = (
            hmac_fingerprint(
                self._config.privacy_hash_secret,
                context.idempotency_key,
                namespace="contact-idempotency",
            )
            if context.idempotency_key
            else None
        )
        payload_digest = (
            hmac_fingerprint(
                self._config.privacy_hash_secret,
                json.dumps(
                    {
                        "name": request.name,
                        "email": normalized_email,
                        "organization": request.organization,
                        "category": request.category,
                        "subject": request.subject,
                        "message": request.message,
                        "consent": request.consent,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ),
                namespace="contact-payload",
            )
            if idempotency_hash
            else None
        )
        if idempotency_hash:
            existing = await self._repository.get_contact_by_idempotency_hash(idempotency_hash)
            if existing is not None:
                if existing.payload_digest != payload_digest:
                    raise ConflictError(
                        "This idempotency key was already used for a different contact request."
                    )
                return ContactReceipt(
                    reference_id=existing.id,
                    accepted_at=existing.created_at,
                )

        allowed = await self._rate_limiter.consume(
            (
                RateLimitRequest(
                    namespace="contact-ip",
                    identity_hash=ip_hash,
                    limit=self._config.ip_limit,
                    window_seconds=self._config.rate_limit_window_seconds,
                ),
                RateLimitRequest(
                    namespace="contact-email",
                    identity_hash=email_hash,
                    limit=self._config.email_limit,
                    window_seconds=self._config.rate_limit_window_seconds,
                ),
            ),
            now=now,
        )
        if not allowed:
            raise RateLimitExceededError(retry_after_seconds=self._config.rate_limit_window_seconds)

        create_result = await self._repository.create_contact(
            NewContactSubmission(
                id=str(uuid.uuid4()),
                name=request.name,
                email=normalized_email,
                organization=request.organization,
                category=request.category,
                subject=request.subject,
                message=request.message,
                consent=request.consent,
                notification_status=("pending" if self._config.email_enabled else "disabled"),
                ip_hash=ip_hash,
                email_hash=email_hash,
                idempotency_hash=idempotency_hash,
                payload_digest=payload_digest,
                created_at=now,
            )
        )
        submission = create_result.submission
        if not create_result.created:
            if submission.payload_digest != payload_digest:
                raise ConflictError(
                    "This idempotency key was already used for a different contact request."
                )
            return ContactReceipt(
                reference_id=submission.id,
                accepted_at=submission.created_at,
            )

        # The outbox intent was committed in the same transaction as the submission.
        if self._config.email_enabled and self._email_client is not None:
            await self.deliver_notification(submission.id)
        return ContactReceipt(reference_id=submission.id, accepted_at=submission.created_at)

    async def deliver_notification(self, submission_id: str, *, force: bool = False) -> bool:
        """Claim and deliver one durable outbox entry with a bounded retry schedule."""

        if not self._config.email_enabled or self._email_client is None:
            return False
        now = datetime.now(UTC)
        claimed = await self._repository.claim_notification(submission_id, now=now, force=force)
        if claimed is None:
            return False
        submission = claimed.submission
        try:
            delivery = await self._email_client.send_contact_notification(
                ContactNotification(
                    submission_id=submission.id,
                    delivery_key=claimed.delivery_key,
                    sender_name=submission.name,
                    sender_email=submission.email,
                    organization=submission.organization,
                    category=submission.category,
                    subject=submission.subject,
                    message=submission.message,
                    submitted_at_iso=submission.created_at.isoformat(),
                )
            )
        except Exception:  # persistence and retry intent must survive provider failures
            logger.exception(
                "contact_notification_failed",
                extra={"submission_id": submission.id},
            )
            failed_at = datetime.now(UTC)
            terminal = claimed.attempt_count >= 5
            delay_seconds = min(3600, 30 * (2 ** (claimed.attempt_count - 1)))
            await self._repository.retry_notification(
                submission.id,
                expected_attempt_count=claimed.attempt_count,
                error_code="provider_unavailable",
                next_attempt_at=(
                    None if terminal else failed_at + timedelta(seconds=delay_seconds)
                ),
                terminal=terminal,
                updated_at=failed_at,
            )
            return False
        completed = await self._repository.complete_notification(
            submission.id,
            expected_attempt_count=claimed.attempt_count,
            provider_message_id=delivery.provider_message_id,
            completed_at=datetime.now(UTC),
        )
        return completed

    async def process_due_notifications(
        self,
        *,
        limit: int = 50,
    ) -> ContactNotificationBatchResult:
        """Drain one bounded due batch through the same lease-safe delivery path."""

        if not 1 <= limit <= 100:
            raise ValueError("notification batch limit must be between 1 and 100")
        if not self._config.email_enabled or self._email_client is None:
            return ContactNotificationBatchResult(
                selected_count=0,
                sent_count=0,
                not_sent_by_this_worker_count=0,
            )
        submission_ids = await self._repository.list_due_notification_ids(
            now=datetime.now(UTC),
            limit=limit,
        )
        sent_count = 0
        for submission_id in submission_ids:
            if await self.deliver_notification(submission_id):
                sent_count += 1
        return ContactNotificationBatchResult(
            selected_count=len(submission_ids),
            sent_count=sent_count,
            not_sent_by_this_worker_count=len(submission_ids) - sent_count,
        )

    async def public_options(self) -> ContactOptionsResponse:
        return ContactOptionsResponse(
            categories=[
                ContactCategoryOption(id="general", label="General inquiry"),
                ContactCategoryOption(id="project", label="Project"),
                ContactCategoryOption(id="collaboration", label="Collaboration"),
                ContactCategoryOption(id="speaking", label="Speaking"),
                ContactCategoryOption(id="sponsorship", label="Sponsorship"),
                ContactCategoryOption(id="other", label="Other"),
            ],
            response_time_label=self._config.response_time_label,
            accepting_messages=await self._is_enabled(),
        )

    async def _is_enabled(self) -> bool:
        enabled = self._config.enabled
        if enabled and self._feature_flags is not None:
            enabled = await self._feature_flags.is_enabled("contact", default=True)
        return enabled


class SponsorshipService:
    def __init__(
        self,
        *,
        repository: EngagementRepository,
        enabled: bool,
        feature_flags: FeatureFlagReader | None = None,
    ) -> None:
        self._repository = repository
        self._enabled = enabled
        self._feature_flags = feature_flags

    async def list_public_options(self) -> SponsorshipOptionsResponse:
        if not await self.is_enabled():
            return SponsorshipOptionsResponse(items=[])
        options = await self._repository.list_public_sponsorship_options()
        items: list[SponsorshipOptionResponse] = []
        for option in options:
            if not is_github_sponsors_destination(option.destination_url):
                logger.warning(
                    "invalid_sponsorship_destination_skipped",
                    extra={"sponsorship_slug": option.slug},
                )
                continue
            items.append(
                SponsorshipOptionResponse(
                    slug=option.slug,
                    title=option.title,
                    description=option.description,
                    kind=option.kind,
                    cta_label=option.cta_label,
                    destination_url=option.destination_url,
                    amount_minor=option.amount_minor,
                    currency=option.currency,
                    recurrence=option.recurrence,
                    rel=("sponsored nofollow noopener" if option.nofollow else "noopener"),
                )
            )
        return SponsorshipOptionsResponse(items=items)

    async def is_enabled(self) -> bool:
        enabled = self._enabled
        if enabled and self._feature_flags is not None:
            enabled = await self._feature_flags.is_enabled("sponsorship", default=True)
        return enabled


class EngagementAdminService:
    """Authenticated management behavior for private contacts and sponsorship."""

    def __init__(
        self,
        repository: EngagementAdminRepository,
        contact_service: ContactService | None = None,
    ) -> None:
        self._repository = repository
        self._contact_service = contact_service

    async def list_contacts(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        status: str | None = None,
    ) -> Page[ContactSubmissionAdminRead]:
        records, total = await self._repository.list_contact_submissions(
            limit=limit,
            offset=offset,
            search=search,
            status=status,
        )
        return Page(
            items=[ContactSubmissionAdminRead.model_validate(asdict(item)) for item in records],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update_contact_status(
        self,
        submission_id: str,
        payload: ContactStatusUpdate,
    ) -> ContactSubmissionAdminRead:
        record = await self._repository.update_contact_status(
            submission_id,
            payload.status,
        )
        if record is None:
            raise NotFoundError("Contact submission not found.")
        return ContactSubmissionAdminRead.model_validate(asdict(record))

    async def retry_contact_notification(self, submission_id: str) -> ContactSubmissionAdminRead:
        if self._contact_service is None:
            raise ConflictError("Contact notification delivery is not configured.")
        record = await self._repository.reset_contact_notification(
            submission_id, next_attempt_at=datetime.now(UTC)
        )
        if record is None:
            raise NotFoundError("Contact submission not found.")
        if record.notification_status in {"sent", "disabled"}:
            raise ConflictError("This contact notification is not retryable.")
        await self._contact_service.deliver_notification(submission_id)
        updated = await self._repository.get_contact_submission(submission_id)
        if updated is None:
            raise NotFoundError("Contact submission not found.")
        return ContactSubmissionAdminRead.model_validate(asdict(updated))

    async def list_sponsorship(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        status: str | None = None,
    ) -> Page[SponsorshipOptionAdminRead]:
        records, total = await self._repository.list_sponsorship_options(
            limit=limit,
            offset=offset,
            search=search,
            status=status,
        )
        return Page(
            items=[SponsorshipOptionAdminRead.model_validate(asdict(item)) for item in records],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def create_sponsorship(
        self,
        payload: SponsorshipOptionCreate,
    ) -> SponsorshipOptionAdminRead:
        values = payload.model_dump(mode="json")
        values.update(
            id=str(uuid.uuid4()),
            is_archived=False,
            updated_at=datetime.now(UTC),
        )
        record = await self._repository.create_sponsorship_option(values)
        return SponsorshipOptionAdminRead.model_validate(asdict(record))

    async def update_sponsorship(
        self,
        option_id: str,
        payload: SponsorshipOptionUpdate,
    ) -> SponsorshipOptionAdminRead:
        changes = payload.model_dump(mode="json", exclude_unset=True)
        if changes.get("is_published") is True:
            changes["is_archived"] = False
        changes["updated_at"] = datetime.now(UTC)
        record = await self._repository.update_sponsorship_option(option_id, changes)
        if record is None:
            raise NotFoundError("Sponsorship option not found.")
        return SponsorshipOptionAdminRead.model_validate(asdict(record))

    async def archive_sponsorship(self, option_id: str) -> SponsorshipOptionAdminRead:
        record = await self._repository.update_sponsorship_option(
            option_id,
            {
                "is_published": False,
                "is_archived": True,
                "updated_at": datetime.now(UTC),
            },
        )
        if record is None:
            raise NotFoundError("Sponsorship option not found.")
        return SponsorshipOptionAdminRead.model_validate(asdict(record))
