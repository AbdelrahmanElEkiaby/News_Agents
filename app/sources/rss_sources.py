from app.models.article import Article
from app.sources.rss import fetch_rss_articles

AL_JAZEERA_ARABIC_RSS_URL = "https://www.aljazeera.net/aljazeerarss"
BBC_NEWS_RSS_URL = "https://feeds.bbci.co.uk/news/rss.xml"


async def fetch_arabic_rss_articles() -> list[Article]:
    return await fetch_rss_articles(
        feed_url=AL_JAZEERA_ARABIC_RSS_URL,
        source_name="Al Jazeera Arabic",
        language="ar",
    )


async def fetch_english_rss_articles() -> list[Article]:
    return await fetch_rss_articles(
        feed_url=BBC_NEWS_RSS_URL,
        source_name="BBC News",
        language="en",
    )
