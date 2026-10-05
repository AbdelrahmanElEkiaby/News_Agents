import logging

from sqlalchemy.orm import Session

from app.models.article import Article
from app.services.source_storage import (
    get_active_sources,
    mark_source_fetch_error,
    mark_source_fetch_started,
    mark_source_fetch_success,
)
from app.sources.source_fetcher import fetch_source

logger = logging.getLogger(__name__)


async def fetch_all_articles(db: Session) -> list[Article]:
    articles: list[Article] = []
    sources = get_active_sources(db)

    for source in sources:
        logger.info("Fetching %s...", source.name)
        mark_source_fetch_started(db, source)

        try:
            source_articles = await fetch_source(source)
        except Exception as error:
            logger.warning("Unable to fetch %s: %s", source.name, error)
            mark_source_fetch_error(db, source, error)
            continue

        articles.extend(source_articles)
        mark_source_fetch_success(db, source)
        logger.info("%s articles received from %s.", len(source_articles), source.name)

    return articles
