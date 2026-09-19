from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ArticleCategory = Literal[
    "technology",
    "ai",
    "business",
    "economy",
    "politics",
    "world",
    "middle_east",
    "science",
    "health",
    "sports",
    "entertainment",
    "other",
]


class Article(BaseModel):
    title: str
    url: str
    source: str
    language: str | None = None
    description: str | None = None
    content: str | None = None
    published_at: datetime | None = None


class ArticleRead(Article):
    id: int
    category: str | None = None
    topics: list[str] | None = None
    summary: str | None = None
    key_points: list[str] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleFetchResult(BaseModel):
    fetched: int
    saved: int
    duplicates: int
    content_updated: int
    classified: int
    summarized: int


class ArticleClassification(BaseModel):
    language: str
    category: ArticleCategory
    topics: list[str]


class ArticleSummary(BaseModel):
    summary: str
    key_points: list[str]
