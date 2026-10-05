from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    source_id: int | None = None
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
    ai_processing_started: bool = False


class ArticleAnalysis(BaseModel):
    language: str
    category: ArticleCategory
    topics: list[str]
    summary: str
    key_points: list[str]


class Preferences(BaseModel):
    topics: list[str]
    languages: list[str]


class FeedRequest(Preferences):
    max_articles: int = Field(default=10, ge=1, le=20)


class ArticleRelevance(BaseModel):
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str


class FeedArticle(BaseModel):
    id: int
    source_id: int | None
    title: str
    url: str
    source: str
    language: str | None
    summary: str | None
    category: str | None
    topics: list[str] | None
    published_at: datetime | None
    score: float
    ai_relevance: float
    freshness_score: float
    topic_match_score: float
    reason: str
