from __future__ import annotations

import enum
import re
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SeedSource(enum.StrEnum):
    RESUME = "resume"
    LINKEDIN = "linkedin"
    CURATED = "curated"


PayloadT = TypeVar("PayloadT", bound=BaseModel)
_SEED_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]{1,158}[a-z0-9]$")
SeedKey = Annotated[
    str,
    Field(
        min_length=3,
        max_length=160,
        pattern=r"^[a-z0-9][a-z0-9._-]{1,158}[a-z0-9]$",
    ),
]


class SeedRecord(BaseModel, Generic[PayloadT]):  # noqa: UP046
    model_config = ConfigDict(extra="forbid")

    seed_key: SeedKey
    payload: PayloadT

    @field_validator("seed_key")
    @classmethod
    def validate_seed_key(cls, value: str) -> str:
        if not _SEED_KEY.fullmatch(value):
            raise ValueError("seed_key must be lowercase and contain only . _ or - separators")
        return value


class SeedStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created: int = 0
    skipped: int = 0

    def add_created(self) -> None:
        self.created += 1

    def add_skipped(self) -> None:
        self.skipped += 1
