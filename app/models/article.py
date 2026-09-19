from datetime import datetime

from pydantic import BaseModel


class Article(BaseModel):
    title: str
    url: str
    source: str
    language: str | None = None
    description: str | None = None
    content: str | None = None
    published_at: datetime | None = None
