"""Discovery adapter over engagement's public service methods."""

from __future__ import annotations

from services.discovery.contracts import DiscoveryBreadcrumb, DiscoveryDocument
from services.engagement.service import ContactService, SponsorshipService


class EngagementDiscoveryProvider:
    def __init__(
        self,
        *,
        contact: ContactService,
        sponsorship: SponsorshipService,
    ) -> None:
        self._contact = contact
        self._sponsorship = sponsorship

    async def list_for_discovery(self) -> list[DiscoveryDocument]:
        documents: list[DiscoveryDocument] = []
        contact_options = await self._contact.public_options()
        if contact_options.accepting_messages:
            documents.append(
                DiscoveryDocument(
                    source_id="engagement:contact",
                    content_type="webpage",
                    path="/contact",
                    title="Contact",
                    description="Send a professional project, speaking, or collaboration inquiry.",
                    breadcrumbs=(DiscoveryBreadcrumb(label="Contact", path="/contact"),),
                )
            )
        sponsorship = await self._sponsorship.list_public_options()
        if await self._sponsorship.is_enabled():
            description = " ".join(item.description for item in sponsorship.items)[:320]
            documents.append(
                DiscoveryDocument(
                    source_id="engagement:sponsorship",
                    content_type="webpage",
                    path="/sponsor",
                    title="Sponsor",
                    description=(
                        description
                        or "GitHub Sponsors provides the direct support path; "
                        "purpose-specific sponsorship inquiries are also open."
                    ),
                    breadcrumbs=(DiscoveryBreadcrumb(label="Sponsor", path="/sponsor"),),
                )
            )
        return documents
