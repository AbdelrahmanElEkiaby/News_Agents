import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.models.article import Article

logger = logging.getLogger(__name__)

TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"


async def fetch_hacker_news_articles(limit: int = 10) -> list[Article]:
    articles: list[Article] = []

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(TOP_STORIES_URL)
            response.raise_for_status()

            story_ids = response.json()[:limit]
            tasks = [fetch_hacker_news_item(client, story_id) for story_id in story_ids]
            results = await asyncio.gather(*tasks)
    except httpx.HTTPError as error:
        logger.warning("Could not fetch Hacker News stories: %s", error)
        return articles
    except ValueError as error:
        logger.warning("Could not read Hacker News response: %s", error)
        return articles

    for result in results:
        if result is not None:
            articles.append(result)

    return articles


async def fetch_hacker_news_item(client: httpx.AsyncClient, story_id: int) -> Article | None:
    try:
        response = await client.get(ITEM_URL.format(item_id=story_id))
        response.raise_for_status()
        item = response.json()

        title = item.get("title", "")
        url = item.get("url", "")

        if not title or not url:
            logger.warning("Skipping Hacker News item %s because title or URL is missing", story_id)
            return None

        published_at = None
        if item.get("time") is not None:
            published_at = datetime.fromtimestamp(item["time"], tz=timezone.utc)

        return Article(
            title=title,
            url=url,
            source="Hacker News",
            language="en",
            description=None,
            content=None,
            published_at=published_at,
        )
    except httpx.HTTPError as error:
        logger.warning("Could not fetch Hacker News item %s: %s", story_id, error)
        return None
    except Exception as error:
        logger.warning("Skipping malformed Hacker News item %s: %s", story_id, error)
        return None
