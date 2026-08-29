"""Assistant request and grounded-answer response contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssistantQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=3, max_length=2000)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("Question contains invalid characters")
        return " ".join(value.split())


class AssistantSource(BaseModel):
    citation: str
    title: str
    content_type: str
    canonical_url: str


class AssistantAnswer(BaseModel):
    request_id: str
    answer: str
    sources: list[AssistantSource]
    grounded: bool
    degraded: bool = False
    input_was_redacted: bool = False
    privacy_notice: str = (
        "Questions are not stored. Operational logs retain only a one-way fingerprint and status."
    )
