import logging

from openai import AsyncOpenAI

from app.config import settings
from app.models.article import ArticleClassification
from app.models.article_db import ArticleDB

logger = logging.getLogger(__name__)


async def classify_article(article: ArticleDB) -> ArticleClassification | None:
    if not settings.openai_api_key:
        logger.warning("Skipping article classification because OPENAI_API_KEY is not set")
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
                        "Classify news articles. Return the detected language, one allowed "
                        "category, and a short list of specific topics."
                    ),
                },
                {
                    "role": "user",
                    "content": article_text,
                },
            ],
            text_format=ArticleClassification,
        )

        return response.output_parsed
    except Exception as error:
        logger.warning("Could not classify article %s: %s", article.id, error)
        return None


def build_article_text(article: ArticleDB) -> str:
    description = article.description or ""
    content = article.content or ""

    short_content = content[:1200]

    return (
        f"Title: {article.title}\n"
        f"Source: {article.source}\n"
        f"Known language: {article.language or 'unknown'}\n"
        f"Description: {description}\n"
        f"Content excerpt: {short_content}"
    )
