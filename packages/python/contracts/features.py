"""Public feature-availability contract shared by optional domain services."""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


class FeatureState(enum.StrEnum):
    UNCONFIGURED = "unconfigured"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class FeatureResolution:
    state: FeatureState
    enabled: bool


class FeatureFlagReader(Protocol):
    async def resolve_feature(self, key: str, *, default: bool) -> FeatureResolution: ...

    async def is_enabled(self, key: str, *, default: bool) -> bool: ...


class FeatureConfigurationReader(Protocol):
    async def get_configuration(self, key: str) -> Mapping[str, object]: ...
