import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import create_database_tables, get_db, get_session_local
from app.models.article import ArticleFetchResult, ArticleRead
from app.models.feed import FeedArticle, FeedRequest
from app.models.source import SourceCreate, SourceRead, SourceUpdate
from app.services.article_storage import get_article_by_id, get_articles
from app.services.pipeline import run_news_pipeline
from app.services.relevance import build_personalized_feed
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.source_storage import (
    create_source,
    disable_source,
    get_source_by_feed_url,
    get_source_by_id,
    get_sources,
    seed_default_sources,
    update_source,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="News Agent API")
app.state.settings = settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    create_database_tables()
    session_local = get_session_local()
    db = session_local()

    try:
        seed_default_sources(db)
    finally:
        db.close()

    app.state.scheduler = start_scheduler()


@app.on_event("shutdown")
def shutdown():
    stop_scheduler()


@app.get("/")
async def read_root():
    return {"message": "News Agent API is running"}


@app.post("/articles/fetch", response_model=ArticleFetchResult)
async def fetch_and_save_articles(db: Session = Depends(get_db)):
    return await run_news_pipeline(db)


@app.get("/articles", response_model=list[ArticleRead])
def list_articles(db: Session = Depends(get_db)):
    return get_articles(db)


@app.get("/articles/{article_id}", response_model=ArticleRead)
def read_article(article_id: int, db: Session = Depends(get_db)):
    article = get_article_by_id(db, article_id)

    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    return article


@app.post("/feed", response_model=list[FeedArticle])
async def read_feed(feed_request: FeedRequest, db: Session = Depends(get_db)):
    articles = get_articles(db)
    return await build_personalized_feed(
        articles=articles,
        preferences=feed_request,
        max_articles=feed_request.max_articles,
    )


@app.get("/sources", response_model=list[SourceRead])
def list_sources(db: Session = Depends(get_db)):
    return get_sources(db)


@app.get("/sources/{source_id}", response_model=SourceRead)
def read_source(source_id: int, db: Session = Depends(get_db)):
    source = get_source_by_id(db, source_id)

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    return source


@app.post("/sources", response_model=SourceRead)
def create_new_source(source_data: SourceCreate, db: Session = Depends(get_db)):
    existing_source = get_source_by_feed_url(db, source_data.feed_url)

    if existing_source is not None:
        raise HTTPException(status_code=400, detail="A source with this feed URL already exists")

    return create_source(db, source_data)


@app.patch("/sources/{source_id}", response_model=SourceRead)
def update_existing_source(
    source_id: int,
    source_data: SourceUpdate,
    db: Session = Depends(get_db),
):
    source = get_source_by_id(db, source_id)

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    if source_data.feed_url and source_data.feed_url != source.feed_url:
        existing_source = get_source_by_feed_url(db, source_data.feed_url)

        if existing_source is not None:
            raise HTTPException(status_code=400, detail="A source with this feed URL already exists")

    return update_source(db, source, source_data)


@app.delete("/sources/{source_id}", response_model=SourceRead)
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = get_source_by_id(db, source_id)

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    return disable_source(db, source)
