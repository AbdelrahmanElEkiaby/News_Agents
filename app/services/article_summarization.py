import logging

from openai import AsyncOpenAI

from app.config import settings
from app.models.article import ArticleSummary
from app.models.article_db import ArticleDB

logger = logging.getLogger(__name__)


async def summarize_article(article: ArticleDB) -> ArticleSummary | None:
    if not settings.openai_api_key:
        logger.warning("Skipping article summarization because OPENAI_API_KEY is not set")
        return None

    article_text = build_article_text(article)
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        response = await client.responses.parse(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Summarize news articles briefly. If the article is Arabic, write the "
                        "summary and key points in Arabic. If the article is English, write them "
                        "in English. Keep the output concise."
                    ),
                },
                {
                    "role": "user",
                    "content": article_text,
                },
            ],
            text_format=ArticleSummary,
        )

        return response.output_parsed
    except Exception as error:
        logger.warning("Could not summarize article %s: %s", article.id, error)
        return None


def build_article_text(article: ArticleDB) -> str:
    description = article.description or ""
    content = article.content or ""
    short_content = content[:1200]

    return (
        f"Title: {article.title}\n"
        f"Source: {article.source}\n"
        f"Known language: {article.language or 'unknown'}\n"
        f"Category: {article.category or 'unknown'}\n"
        f"Topics: {article.topics or []}\n"
        f"Description: {description}\n"
        f"Content excerpt: {short_content}"
    )
