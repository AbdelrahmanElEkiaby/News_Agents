from fastapi import FastAPI

from app.config import settings
from app.models.article import Article
from app.services.news_collection import fetch_all_articles

app = FastAPI(title="News Agent API")
app.state.settings = settings


@app.get("/")
async def read_root():
    return {"message": "News Agent API is running"}


@app.get("/articles/fetch", response_model=list[Article])
async def fetch_articles():
    return await fetch_all_articles()
