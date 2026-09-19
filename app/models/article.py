from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArticleFetchResult(BaseModel):
    fetched: int
    saved: int
    duplicates: int
