"""SEO, AEO, GEO, and agent-discovery policy service."""

from services.discovery.contracts import DiscoveryContentProvider, DiscoveryDocument
from services.discovery.service import DiscoveryService

__all__ = ["DiscoveryContentProvider", "DiscoveryDocument", "DiscoveryService"]
