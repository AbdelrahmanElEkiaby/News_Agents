from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import UserDB
from app.schemas.article import ArticleFetchResult, ArticleRead, FeedArticle, FeedRequest
from app.services.article_service import (
    get_article_by_id,
    get_articles_for_user,
)
from app.services.news_pipeline import (
    process_missing_articles_in_background,
    run_news_pipeline,
)
from app.services.relevance import build_personalized_feed
from app.services.auth_service import get_current_user
from app.services.user_service import get_subscription

router = APIRouter()


@router.post("/articles/fetch", response_model=ArticleFetchResult)
async def fetch_and_save_articles(
    background_tasks: BackgroundTasks,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await run_news_pipeline(db, process_ai=False)

    if settings.openai_api_key:
        background_tasks.add_task(process_missing_articles_in_background)
        result["ai_processing_started"] = True

    return result


@router.post("/articles/process-missing")
async def process_missing_articles(
    background_tasks: BackgroundTasks,
    current_user: UserDB = Depends(get_current_user),
):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")

    background_tasks.add_task(process_missing_articles_in_background)
    return {"message": "Missing article summaries were queued for background processing."}


@router.get("/articles", response_model=list[ArticleRead])
def list_articles(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_articles_for_user(db, current_user.id)


@router.get("/articles/{article_id}", response_model=ArticleRead)
def read_article(
    article_id: int,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)

    if (
        article is None
        or article.source_id is None
        or get_subscription(db, current_user.id, article.source_id) is None
    ):
        raise HTTPException(status_code=404, detail="Article not found")

    return article


@router.post("/feed", response_model=list[FeedArticle])
async def read_feed(
    feed_request: FeedRequest,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    articles = get_articles_for_user(db, current_user.id)

    return await build_personalized_feed(
        articles=articles,
        preferences=feed_request,
        max_articles=feed_request.max_articles,
    )
