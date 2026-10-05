import logging

from app.models.article import Article
from app.models.source_db import SourceDB
from app.sources.rss import fetch_rss_source

logger = logging.getLogger(__name__)


async def fetch_source(source: SourceDB) -> list[Article]:
    if source.source_type == "rss":
        return await fetch_rss_source(source)

    logger.warning("Unsupported source type %s for %s", source.source_type, source.name)
    return []
