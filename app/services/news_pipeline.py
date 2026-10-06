import asyncio
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_session_local
from app.schemas.article import Article
from app.services.article_classification import classify_articles
from app.services.article_content import fetch_article_contents
from app.services.article_service import (
    get_articles_missing_classification,
    save_article_classifications,
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

logger = logging.getLogger(__name__)
classification_lock = asyncio.Lock()


async def fetch_all_articles(
    db: Session,
    source_ids: set[int] | None = None,
) -> list[Article]:
    articles: list[Article] = []
    sources = get_active_sources(db)

    if source_ids is not None:
        sources = [source for source in sources if source.id in source_ids]

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


async def run_news_pipeline(
    db: Session,
    classify_missing: bool = True,
    source_ids: set[int] | None = None,
) -> dict[str, int | bool]:
    logger.info("Fetching articles...")
    articles = await fetch_all_articles(db, source_ids=source_ids)
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

    if classify_missing:
        async with classification_lock:
            classified_count = await process_missing_classifications(
                db,
                source_ids=source_ids,
            )

    logger.info("Pipeline completed.")
    return {
        **stats,
        "classified": classified_count,
        "summarized": 0,
        "ai_processing_started": False,
    }


async def process_missing_classifications(
    db: Session,
    limit: int = 100,
    source_ids: set[int] | None = None,
) -> int:
    articles_to_classify = get_articles_missing_classification(
        db,
        limit=limit,
        source_ids=source_ids,
    )
    logger.info("%s articles are waiting for Jev classification.", len(articles_to_classify))

    classifications = await classify_articles(articles_to_classify)
    classified_count = save_article_classifications(db, classifications)
    logger.info("Jev classification completed for %s articles.", classified_count)
    return classified_count

async def process_missing_classifications_in_background(limit: int = 100) -> None:
    if not settings.jev_api_key:
        logger.warning("Background classification skipped: JEV_API_KEY is not set")
        return

    async with classification_lock:
        session_local = get_session_local()
        db = session_local()

        try:
            await process_missing_classifications(db, limit=limit)
        except Exception as error:
            db.rollback()
            logger.exception("Background article classification failed: %s", error)
        finally:
            db.close()
