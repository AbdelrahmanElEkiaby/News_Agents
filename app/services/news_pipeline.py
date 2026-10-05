import asyncio
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_session_local
from app.schemas.article import Article
from app.services.article_analysis import analyze_articles
from app.services.article_service import (
    get_articles_missing_analysis,
    save_article_analyses,
    save_article_contents,
    save_new_articles,
)
from app.services.rss_service import fetch_source
from app.services.source_service import (
    get_active_sources,
    mark_source_fetch_error,
    mark_source_fetch_started,
    mark_source_fetch_success,
)
from app.services.article_content import fetch_article_contents

logger = logging.getLogger(__name__)
analysis_lock = asyncio.Lock()


async def fetch_all_articles(db: Session) -> list[Article]:
    articles: list[Article] = []
    sources = get_active_sources(db)

    for source in sources:
        logger.info("Fetching %s...", source.name)
        mark_source_fetch_started(db, source)

    results = await asyncio.gather(
        *(fetch_source(source) for source in sources),
        return_exceptions=True,
    )

    for source, result in zip(sources, results, strict=True):
        if isinstance(result, BaseException):
            logger.warning("Unable to fetch %s: %s", source.name, result)
            mark_source_fetch_error(db, source, result)
            continue

        articles.extend(result)
        mark_source_fetch_success(db, source)
        logger.info("%s articles received from %s.", len(result), source.name)

    return articles


async def run_news_pipeline(db: Session, process_ai: bool = True) -> dict[str, int | bool]:
    logger.info("Fetching articles...")
    articles = await fetch_all_articles(db)
    logger.info("%s articles received.", len(articles))

    stats, saved_articles = save_new_articles(db, articles)
    logger.info("%s new articles saved.", stats["saved"])
    logger.info("%s duplicate articles skipped.", stats["duplicates"])

    articles_needing_content = [article for article in saved_articles if not article.content]
    contents = await fetch_article_contents(articles_needing_content)
    content_updated_count = save_article_contents(db, contents)
    stats["content_updated"] += content_updated_count
    logger.info("%s article bodies downloaded.", content_updated_count)

    classified_count = 0
    summarized_count = 0

    if process_ai:
        async with analysis_lock:
            classified_count, summarized_count = await process_missing_articles(db)

    logger.info("Pipeline completed.")
    return {
        **stats,
        "classified": classified_count,
        "summarized": summarized_count,
        "ai_processing_started": False,
    }


async def process_missing_articles(db: Session, limit: int = 100) -> tuple[int, int]:
    articles = get_articles_missing_analysis(db, limit=limit)
    logger.info("%s articles are waiting for AI analysis.", len(articles))

    analyses = await analyze_articles(articles)
    counts = save_article_analyses(db, analyses)
    logger.info("AI analysis completed for %s articles.", len(analyses))
    return counts


async def process_missing_articles_in_background(limit: int = 100) -> None:
    if not settings.openai_api_key:
        logger.warning("Background article analysis skipped: OPENAI_API_KEY is not set")
        return

    async with analysis_lock:
        session_local = get_session_local()
        db = session_local()

        try:
            await process_missing_articles(db, limit=limit)
        except Exception as error:
            db.rollback()
            logger.exception("Background article analysis failed: %s", error)
        finally:
            db.close()
