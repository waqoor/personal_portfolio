"""Deliberate public and persistence contracts for engagement behavior."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class NewContactSubmission:
    id: str
    name: str
    email: str
    organization: str | None
    category: str
    subject: str | None
    message: str
    consent: bool
    notification_status: str
    ip_hash: str
    email_hash: str
    idempotency_hash: str | None
    payload_digest: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredContactSubmission:
    id: str
    name: str
    email: str
    organization: str | None
    category: str
    subject: str | None
    message: str
    payload_digest: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ClaimedContactNotification:
    submission: StoredContactSubmission
    delivery_key: str
    attempt_count: int


@dataclass(frozen=True, slots=True)
class ContactCreateResult:
    submission: StoredContactSubmission
    created: bool


@dataclass(frozen=True, slots=True)
class PublicSponsorshipOption:
    slug: str
    title: str
    description: str
    kind: str
    cta_label: str
    destination_url: str
    amount_minor: int | None
    currency: str | None
    recurrence: str | None
    nofollow: bool


@dataclass(frozen=True, slots=True)
class AdminContactSubmission:
    id: str
    name: str
    email: str
    organization: str | None
    category: str
    subject: str | None
    message: str
    consent: bool
    status: str
    notification_status: str
    notification_error_code: str | None
    notification_attempt_count: int
    notification_next_attempt_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AdminSponsorshipOption:
    id: str
    slug: str
    title: str
    description: str
    kind: str
    cta_label: str
    destination_url: str
    amount_minor: int | None
    currency: str | None
    recurrence: str | None
    sort_order: int
    is_published: bool
    is_archived: bool
    nofollow: bool
    updated_at: datetime


class EngagementRepository(Protocol):
    async def get_contact_by_idempotency_hash(
        self, idempotency_hash: str
    ) -> StoredContactSubmission | None: ...

    async def create_contact(self, submission: NewContactSubmission) -> ContactCreateResult: ...

    async def list_due_notification_ids(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> list[str]: ...

    async def claim_notification(
        self,
        submission_id: str,
        *,
        now: datetime,
        force: bool = False,
    ) -> ClaimedContactNotification | None: ...

    async def complete_notification(
        self,
        submission_id: str,
        *,
        expected_attempt_count: int,
        provider_message_id: str | None,
        completed_at: datetime,
    ) -> bool: ...

    async def retry_notification(
        self,
        submission_id: str,
        *,
        expected_attempt_count: int,
        error_code: str,
        next_attempt_at: datetime | None,
        terminal: bool,
        updated_at: datetime,
    ) -> bool: ...

    async def list_public_sponsorship_options(self) -> list[PublicSponsorshipOption]: ...


class EngagementAdminRepository(Protocol):
    async def get_contact_submission(self, submission_id: str) -> AdminContactSubmission | None: ...

    async def list_contact_submissions(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[AdminContactSubmission], int]: ...

    async def update_contact_status(
        self, submission_id: str, status: str
    ) -> AdminContactSubmission | None: ...

    async def reset_contact_notification(
        self, submission_id: str, *, next_attempt_at: datetime
    ) -> AdminContactSubmission | None: ...

    async def list_sponsorship_options(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[AdminSponsorshipOption], int]: ...

    async def create_sponsorship_option(
        self, values: Mapping[str, object]
    ) -> AdminSponsorshipOption: ...

    async def update_sponsorship_option(
        self, option_id: str, changes: Mapping[str, object]
    ) -> AdminSponsorshipOption | None: ...
