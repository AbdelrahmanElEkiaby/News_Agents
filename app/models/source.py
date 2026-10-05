from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SourceType = Literal["rss"]


class SourceCreate(BaseModel):
    name: str = Field(min_length=1)
    website_url: str | None = None
    feed_url: str | None = None
    language: str = Field(min_length=2, max_length=5)
    source_type: SourceType = "rss"

    @field_validator("name", "language")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return value.lower()

    @model_validator(mode="after")
    def validate_rss_feed_url(self):
        if self.source_type == "rss" and not self.feed_url:
            raise ValueError("feed_url is required for RSS sources")

        return self


class SourceWebsiteCreate(BaseModel):
    url: str = Field(min_length=1)
    name: str | None = None
    language: str = Field(default="en", min_length=2, max_length=5)

    @field_validator("url", "name", "language")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip()

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return value.lower()


class SourceDiscoverRequest(BaseModel):
    url: str = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        return value.strip()


class DiscoveredFeed(BaseModel):
    title: str
    feed_url: str
    feed_type: str
    discovery_method: str
    item_count: int
    latest_published_at: datetime | None
    score: int


class SourceDiscoverResponse(BaseModel):
    website_url: str
    feed_url: str | None
    feed_found: bool
    message: str
    feeds: list[DiscoveredFeed] = Field(default_factory=list)
    recommended_feed: str | None = None


class SourceUpdate(BaseModel):
    name: str | None = None
    website_url: str | None = None
    feed_url: str | None = None
    language: str | None = Field(default=None, min_length=2, max_length=5)
    source_type: SourceType | None = None
    is_active: bool | None = None

    @field_validator("name", "language")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.strip()

    @field_validator("language")
    @classmethod
    def normalize_optional_language(cls, value: str | None) -> str | None:
        if value is None:
            return None

        return value.lower()


class SourceRead(BaseModel):
    id: int
    name: str
    website_url: str | None
    feed_url: str | None
    language: str
    source_type: str
    is_active: bool
    last_fetched_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
