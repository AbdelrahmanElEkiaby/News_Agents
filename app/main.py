import logging
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import create_database_tables, get_db, get_session_local
from app.models.article import ArticleFetchResult, ArticleRead
from app.models.feed import FeedArticle, FeedRequest
from app.models.source import (
    SourceCreate,
    SourceDiscoverRequest,
    SourceDiscoverResponse,
    SourceRead,
    SourceUpdate,
    SourceWebsiteCreate,
)
from app.services.article_storage import get_article_by_id, get_articles
from app.services.pipeline import process_missing_articles_in_background, run_news_pipeline
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
from app.sources.feed_discovery import discover_feeds, normalize_website_url, validate_feed_url

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_database_tables()
    session_local = get_session_local()
    db = session_local()

    try:
        seed_default_sources(db)
    finally:
        db.close()

    app.state.scheduler = start_scheduler()

    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="News Agent API", lifespan=lifespan)
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


@app.get("/")
async def read_root():
    return {"message": "News Agent API is running"}


@app.post("/articles/fetch", response_model=ArticleFetchResult)
async def fetch_and_save_articles(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    result = await run_news_pipeline(db, process_ai=False)

    if settings.openai_api_key:
        background_tasks.add_task(process_missing_articles_in_background)
        result["ai_processing_started"] = True

    return result


@app.post("/articles/process-missing")
async def process_missing_articles(background_tasks: BackgroundTasks):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")

    background_tasks.add_task(process_missing_articles_in_background)
    return {"message": "Missing article summaries were queued for background processing."}


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


@app.post("/sources/discover", response_model=SourceDiscoverResponse)
async def discover_source(source_data: SourceDiscoverRequest):
    website_url = normalize_website_url(source_data.url)
    feeds = await discover_feeds(website_url)

    if not feeds:
        return SourceDiscoverResponse(
            website_url=website_url,
            feed_url=None,
            feed_found=False,
            message="No RSS or Atom feed found.",
            feeds=[],
            recommended_feed=None,
        )

    recommended_feed = feeds[0]

    return SourceDiscoverResponse(
        website_url=website_url,
        feed_url=recommended_feed.feed_url,
        feed_found=True,
        message=f"Found {len(feeds)} RSS or Atom feed(s).",
        feeds=feeds,
        recommended_feed=recommended_feed.feed_url,
    )


@app.post("/sources/from-website", response_model=SourceRead)
async def create_source_from_website(
    source_data: SourceWebsiteCreate,
    db: Session = Depends(get_db),
):
    website_url = normalize_website_url(source_data.url)
    feeds = await discover_feeds(website_url)

    if not feeds:
        raise HTTPException(status_code=400, detail="No RSS or Atom feed found.")

    recommended_feed = feeds[0]
    feed_url = recommended_feed.feed_url

    existing_source = get_source_by_feed_url(db, feed_url)

    if existing_source is not None:
        raise HTTPException(status_code=400, detail="A source with this feed URL already exists")

    source_name = source_data.name or recommended_feed.title or get_name_from_url(website_url)
    create_data = SourceCreate(
        name=source_name,
        website_url=website_url,
        feed_url=feed_url,
        language=source_data.language,
        source_type="rss",
    )

    return create_source(db, create_data)


@app.get("/sources/{source_id}", response_model=SourceRead)
def read_source(source_id: int, db: Session = Depends(get_db)):
    source = get_source_by_id(db, source_id)

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    return source


@app.post("/sources", response_model=SourceRead)
async def create_new_source(source_data: SourceCreate, db: Session = Depends(get_db)):
    if source_data.source_type == "rss":
        feed_url = normalize_website_url(source_data.feed_url or "")

        if not await validate_feed_url(feed_url):
            raise HTTPException(status_code=400, detail="The RSS or Atom feed URL is not valid")

        source_data.feed_url = feed_url

    existing_source = get_source_by_feed_url(db, source_data.feed_url)

    if existing_source is not None:
        raise HTTPException(status_code=400, detail="A source with this feed URL already exists")

    return create_source(db, source_data)


@app.patch("/sources/{source_id}", response_model=SourceRead)
async def update_existing_source(
    source_id: int,
    source_data: SourceUpdate,
    db: Session = Depends(get_db),
):
    source = get_source_by_id(db, source_id)

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    updated_source_type = source_data.source_type or source.source_type
    updated_feed_url = source.feed_url

    if "feed_url" in source_data.model_fields_set:
        updated_feed_url = source_data.feed_url

    if updated_source_type == "rss":
        if not updated_feed_url:
            raise HTTPException(status_code=400, detail="feed_url is required for RSS sources")

        normalized_feed_url = normalize_website_url(updated_feed_url)

        if normalized_feed_url != source.feed_url or source.source_type != "rss":
            if not await validate_feed_url(normalized_feed_url):
                raise HTTPException(status_code=400, detail="The RSS or Atom feed URL is not valid")

        source_data.feed_url = normalized_feed_url

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


def get_name_from_url(url: str) -> str:
    hostname = urlparse(url).netloc.replace("www.", "")

    if not hostname:
        return "New Source"

    return hostname.split(":")[0]
