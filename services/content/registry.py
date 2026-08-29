from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files

from packages.python.common.errors import ValidationError
from services.content.models import HomepageSectionType


@dataclass(frozen=True, slots=True)
class SectionDefinition:
    variants: frozenset[str]
    default_variant: str
    default_limit: int | None = None
    feature_key: str | None = None


class HomepageSectionRegistry:
    """Allow-list for data-backed section types and supported rendering variants."""

    def __init__(self, featured_project_limit: int = 5) -> None:
        raw = json.loads(
            files("packages.python.contracts")
            .joinpath("homepage_sections.json")
            .read_text(encoding="utf-8")
        )
        if not isinstance(raw, dict):
            raise RuntimeError("Homepage section registry must be an object")
        self._definitions = {}
        for section_type in HomepageSectionType:
            value = raw.get(section_type.value)
            if not isinstance(value, dict):
                raise RuntimeError(f"Missing homepage registry entry: {section_type.value}")
            variants = value.get("variants")
            default_variant = value.get("default_variant")
            default_limit = value.get("default_limit")
            feature_key = value.get("feature_key")
            if not isinstance(variants, list) or not all(
                isinstance(variant, str) for variant in variants
            ):
                raise RuntimeError(f"Invalid variants for section: {section_type.value}")
            if default_limit is not None and not isinstance(default_limit, int):
                raise RuntimeError(f"Invalid default limit for section: {section_type.value}")
            if feature_key is not None and not isinstance(feature_key, str):
                raise RuntimeError(f"Invalid feature key for section: {section_type.value}")
            if not isinstance(default_variant, str) or default_variant not in variants:
                raise RuntimeError(f"Invalid default variant for section: {section_type.value}")
            if section_type is HomepageSectionType.SELECTED_WORK:
                default_limit = featured_project_limit
            self._definitions[section_type] = SectionDefinition(
                frozenset(variants), default_variant, default_limit, feature_key
            )

    def validate(self, section_type: HomepageSectionType, variant: str) -> None:
        definition = self._definitions.get(section_type)
        if definition is None or variant not in definition.variants:
            raise ValidationError(
                f"Variant '{variant}' is not supported for section '{section_type.value}'."
            )

    def canonical_persisted_variant(self, section_type: HomepageSectionType, variant: str) -> str:
        """Project a previously stored variant onto the current allow-list.

        This is deliberately separate from ``validate``: new client input remains
        strict, while a deployment can still read and round-trip a row saved by an
        older registry without exposing or executing the retired variant.
        """

        definition = self._definitions[section_type]
        return variant if variant in definition.variants else definition.default_variant

    def default_limit(self, section_type: HomepageSectionType) -> int | None:
        return self._definitions[section_type].default_limit

    def default_variant(self, section_type: HomepageSectionType) -> str:
        return self._definitions[section_type].default_variant

    def feature_key(self, section_type: HomepageSectionType) -> str | None:
        return self._definitions[section_type].feature_key
