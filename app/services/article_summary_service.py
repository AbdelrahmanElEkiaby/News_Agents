from datetime import datetime, timedelta, timezone
from math import ceil

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.article import ArticleDB
from app.models.user import UserDB
from app.services.article_summarization import generate_article_summary

SUMMARY_RETRY_COOLDOWN = timedelta(seconds=60)
SUMMARY_PROCESSING_TIMEOUT = timedelta(minutes=5)
SUMMARY_USER_RATE_LIMIT = 5
SUMMARY_USER_RATE_WINDOW = timedelta(minutes=1)


class SummaryError(Exception):
    """Base error for on-demand summary generation."""


class SummaryNotReadyError(SummaryError):
    pass


class SummaryConfigurationError(SummaryError):
    pass


class SummaryAlreadyProcessingError(SummaryError):
    pass


class SummaryCooldownError(SummaryError):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Try again in {retry_after_seconds} seconds.")


class SummaryRateLimitError(SummaryCooldownError):
    pass


class SummaryGenerationError(SummaryError):
    pass


async def get_or_generate_summary(db: Session, article_id: int, user_id: int) -> ArticleDB:
    """Return a cached summary or reserve and execute one generation request."""
    _lock_user(db, user_id)
    article = _get_article_for_update(db, article_id)
    if article is None:
        raise SummaryNotReadyError("Article not found.")

    if article.summary:
        if article.summary_status != "completed":
            article.summary_status = "completed"
            article.summary_generated_at = article.summary_generated_at or _utc_now()
            article.summary_error = None
            db.commit()
            db.refresh(article)
        else:
            db.rollback()
        return article

    if not settings.openai_api_key:
        db.rollback()
        raise SummaryConfigurationError("OPENAI_API_KEY is not configured.")

    if not _has_complete_classification(article):
        db.rollback()
        raise SummaryNotReadyError("The article is still waiting for Jev classification.")

    now = _utc_now()
    request_age = _age_since(article.summary_requested_at, now)

    if (
        article.summary_status == "processing"
        and request_age is not None
        and request_age < SUMMARY_PROCESSING_TIMEOUT
    ):
        db.rollback()
        raise SummaryAlreadyProcessingError("A summary request is already running.")

    if (
        article.summary_status == "failed"
        and request_age is not None
        and request_age < SUMMARY_RETRY_COOLDOWN
    ):
        retry_after = ceil((SUMMARY_RETRY_COOLDOWN - request_age).total_seconds())
        db.rollback()
        raise SummaryCooldownError(max(retry_after, 1))

    rate_limit_retry_after = _get_user_rate_limit_retry_after(db, user_id, now)
    if rate_limit_retry_after is not None:
        db.rollback()
        raise SummaryRateLimitError(rate_limit_retry_after)

    article.summary_status = "processing"
    article.summary_requested_at = now
    article.summary_requested_by_user_id = user_id
    article.summary_error = None
    db.commit()
    db.refresh(article)
    db.expunge(article)
    db.rollback()

    summary = await generate_article_summary(article)
    article = _get_article_for_update(db, article_id)
    if article is None:
        db.rollback()
        raise SummaryGenerationError("The article no longer exists.")

    if summary is None:
        article.summary_status = "failed"
        article.summary_error = "OpenAI did not return a valid structured summary."
        db.commit()
        raise SummaryGenerationError("Summary generation failed. Try again later.")

    article.summary = summary.summary
    article.key_points = summary.key_points
    article.summary_status = "completed"
    article.summary_generated_at = _utc_now()
    article.summary_error = None
    db.commit()
    db.refresh(article)
    return article


def _get_article_for_update(db: Session, article_id: int) -> ArticleDB | None:
    return db.scalar(
        select(ArticleDB)
        .where(ArticleDB.id == article_id)
        .with_for_update()
    )


def _lock_user(db: Session, user_id: int) -> None:
    db.scalar(select(UserDB.id).where(UserDB.id == user_id).with_for_update())


def _get_user_rate_limit_retry_after(
    db: Session,
    user_id: int,
    now: datetime,
) -> int | None:
    window_start = now - SUMMARY_USER_RATE_WINDOW
    recent_requests = list(
        db.scalars(
            select(ArticleDB.summary_requested_at)
            .where(
                ArticleDB.summary_requested_by_user_id == user_id,
                ArticleDB.summary_requested_at >= window_start,
            )
            .order_by(ArticleDB.summary_requested_at.asc())
        )
    )

    if len(recent_requests) < SUMMARY_USER_RATE_LIMIT:
        return None

    retry_at = recent_requests[0] + SUMMARY_USER_RATE_WINDOW
    return max(ceil((retry_at - now).total_seconds()), 1)


def _has_complete_classification(article: ArticleDB) -> bool:
    return all(
        value is not None
        for value in (
            article.language,
            article.category,
            article.topics,
            article.importance,
        )
    )


def _age_since(value: datetime | None, now: datetime) -> timedelta | None:
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return now - value


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
