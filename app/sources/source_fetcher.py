import logging

from app.models.article import Article
from app.models.source_db import SourceDB
from app.sources.hacker_news import fetch_hacker_news_articles
from app.sources.rss import fetch_rss_source

logger = logging.getLogger(__name__)


async def fetch_source(source: SourceDB) -> list[Article]:
    if source.source_type == "rss":
        return await fetch_rss_source(source)

    if source.source_type == "api":
        return await fetch_api_source(source)

    logger.warning("Unsupported source type %s for %s", source.source_type, source.name)
    return []


async def fetch_api_source(source: SourceDB) -> list[Article]:
    if source.name.lower() == "hacker news":
        return await fetch_hacker_news_articles()

    logger.warning("No API fetcher is configured for %s", source.name)
    return []
