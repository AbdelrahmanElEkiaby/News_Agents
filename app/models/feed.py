from datetime import datetime

from pydantic import BaseModel, Field

from app.models.preference import Preferences


class FeedRequest(Preferences):
    max_articles: int = Field(default=10, ge=1, le=20)


class ArticleRelevance(BaseModel):
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str


class FeedArticle(BaseModel):
    id: int
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
