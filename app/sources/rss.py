import calendar
import logging
from datetime import datetime, timezone

import feedparser
import httpx

from app.models.article import Article

logger = logging.getLogger(__name__)


async def fetch_rss_articles(
    feed_url: str,
    source_name: str,
    language: str,
    limit: int = 10,
) -> list[Article]:
    articles: list[Article] = []

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(feed_url)
            response.raise_for_status()
    except httpx.HTTPError as error:
        logger.warning("Could not fetch RSS feed from %s: %s", source_name, error)
        return articles

    parsed_feed = feedparser.parse(response.content)

    if parsed_feed.bozo:
        logger.warning("RSS feed from %s may be malformed", source_name)

    for entry in parsed_feed.entries[:limit]:
        article = parse_rss_entry(entry, source_name, language)

        if article is not None:
            articles.append(article)

    return articles


def parse_rss_entry(entry, source_name: str, language: str) -> Article | None:
    try:
        title = clean_text(entry.get("title", ""))
        url = entry.get("link", "")

        if not title or not url:
            logger.warning("Skipping RSS entry from %s because title or URL is missing", source_name)
            return None

        description = clean_text(entry.get("summary") or entry.get("description") or "")
        published_at = parse_rss_date(entry)

        return Article(
            title=title,
            url=url,
            source=source_name,
            language=language,
            description=description or None,
            content=None,
            published_at=published_at,
        )
    except Exception as error:
        logger.warning("Skipping malformed RSS entry from %s: %s", source_name, error)
        return None


def parse_rss_date(entry) -> datetime | None:
    published_time = entry.get("published_parsed") or entry.get("updated_parsed")

    if published_time is None:
        return None

    timestamp = calendar.timegm(published_time)
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def clean_text(value: str) -> str:
    return " ".join(value.split())
