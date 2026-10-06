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
    process_missing_classifications_in_background,
    run_news_pipeline,
)
from app.services.relevance import build_personalized_feed
from app.services.article_summary_service import (
    SummaryAlreadyProcessingError,
    SummaryConfigurationError,
    SummaryCooldownError,
    SummaryGenerationError,
    SummaryNotReadyError,
    SummaryRateLimitError,
    get_or_generate_summary,
)
from app.services.auth_service import get_current_user
from app.services.user_service import get_subscription, get_user_sources

router = APIRouter()


@router.post("/articles/fetch", response_model=ArticleFetchResult)
async def fetch_and_save_articles(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subscribed_sources = get_user_sources(db, current_user.id)

    if not subscribed_sources:
        raise HTTPException(
            status_code=400,
            detail="Subscribe to at least one source before scanning.",
        )

    return await run_news_pipeline(
        db,
        source_ids={source.id for source in subscribed_sources},
    )


@router.post("/articles/process-missing")
async def process_missing_classifications(
    background_tasks: BackgroundTasks,
    current_user: UserDB = Depends(get_current_user),
):
    if not settings.jev_api_key:
        raise HTTPException(
            status_code=503,
            detail="JEV_API_KEY is not configured",
        )

    background_tasks.add_task(process_missing_classifications_in_background)
    return {"message": "Missing article classifications were queued."}


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


@router.post("/articles/{article_id}/summary", response_model=ArticleRead)
async def generate_article_summary(
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

    try:
        return await get_or_generate_summary(db, article_id, current_user.id)
    except SummaryConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except SummaryAlreadyProcessingError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
            headers={"Retry-After": "5"},
        ) from error
    except SummaryRateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail=(
                "Summary limit reached. "
                f"Try again in {error.retry_after_seconds} seconds."
            ),
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    except SummaryCooldownError as error:
        raise HTTPException(
            status_code=429,
            detail=str(error),
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
    except SummaryNotReadyError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SummaryGenerationError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


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
