"""Validated input and AI output contracts; originals and generated fields stay separate."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

INTERESTS = ("Basketball", "Guitar", "Coursework", "Programming", "Running", "Cooking", "Photography")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True, revalidate_instances="always")


class MemoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=12000)
    occurred_at: date
    title: str = Field(default="", max_length=160)
    location: str | None = Field(default=None, max_length=160)

    @field_validator("content")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Write something about your memory")
        return value


class Metadata(StrictModel):
    summary: str = Field(min_length=1, max_length=1200)
    tags: list[str] = Field(max_length=12)
    activity: Literal["sports", "music", "study", "travel", "social", "everyday", "other"]
    people: list[str] = Field(max_length=12)
    location: str | None
    is_milestone: bool
    chapter_topics: list[str] = Field(max_length=8)

    @field_validator("tags", "people", "chapter_topics")
    @classmethod
    def clean_lists(cls, values):
        if any(not v.strip() or len(v) > 160 for v in values):
            raise ValueError("Labels must contain 1–160 characters")
        return list(dict.fromkeys(v.strip() for v in values))


class Statement(StrictModel):
    text: str = Field(min_length=1, max_length=2000)
    entry_ids: list[int] = Field(min_length=1, max_length=100)


class Narrative(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    overview: Statement
    highlights: list[Statement] = Field(max_length=8)
    conclusion: Statement

    def verify_sources(self, available_ids: set[int]):
        for statement in [self.overview, *self.highlights, self.conclusion]:
            if not set(statement.entry_ids) <= available_ids:
                raise ValueError("Generated narrative references unknown memories")
        return self

    def source_ids(self):
        return sorted({i for s in [self.overview, *self.highlights, self.conclusion] for i in s.entry_ids})
