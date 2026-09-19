import asyncio

from app.models.article import Article
from app.sources.hacker_news import fetch_hacker_news_articles
from app.sources.rss_sources import fetch_arabic_rss_articles, fetch_english_rss_articles


async def fetch_all_articles() -> list[Article]:
    results = await asyncio.gather(
        fetch_hacker_news_articles(),
        fetch_arabic_rss_articles(),
        fetch_english_rss_articles(),
    )

    articles: list[Article] = []

    for source_articles in results:
        articles.extend(source_articles)

    return articles
