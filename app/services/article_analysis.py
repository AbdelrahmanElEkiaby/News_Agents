import asyncio
import logging

from openai import AsyncOpenAI

from app.config import settings
from app.models.article import ArticleAnalysis
from app.models.article_db import ArticleDB

logger = logging.getLogger(__name__)


async def analyze_articles(
    articles: list[ArticleDB],
    max_concurrency: int = 3,
) -> list[tuple[ArticleDB, ArticleAnalysis]]:
    if not articles:
        return []

    if not settings.openai_api_key:
        logger.warning("Skipping article analysis because OPENAI_API_KEY is not set")
        return []

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    semaphore = asyncio.Semaphore(max_concurrency)

    async def analyze_one(
        article: ArticleDB,
    ) -> tuple[ArticleDB, ArticleAnalysis] | None:
        async with semaphore:
            analysis = await analyze_article(client, article)

        if analysis is None:
            return None

        return article, analysis

    try:
        results = await asyncio.gather(*(analyze_one(article) for article in articles))
    finally:
        await client.close()

    return [result for result in results if result is not None]


async def analyze_article(
    client: AsyncOpenAI,
    article: ArticleDB,
) -> ArticleAnalysis | None:
    try:
        response = await client.responses.parse(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Analyze this news article in one response. Detect its language; "
                        "choose one allowed category; provide a short list of specific topics; "
                        "and write a concise summary with key points. Write the summary and "
                        "key points in the article's language."
                    ),
                },
                {
                    "role": "user",
                    "content": build_article_text(article),
                },
            ],
            text_format=ArticleAnalysis,
        )
        return response.output_parsed
    except Exception as error:
        logger.warning("Could not analyze article %s: %s", article.id, error)
        return None


def build_article_text(article: ArticleDB) -> str:
    return (
        f"Title: {article.title}\n"
        f"Source: {article.source}\n"
        f"Known language: {article.language or 'unknown'}\n"
        f"Description: {article.description or ''}\n"
        f"Content excerpt: {(article.content or '')[:2000]}"
    )
