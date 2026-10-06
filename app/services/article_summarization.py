import logging

from openai import AsyncOpenAI

from app.config import settings
from app.models.article import ArticleDB
from app.schemas.article import ArticleSummary
from app.services.article_context import format_article_context

logger = logging.getLogger(__name__)


async def generate_article_summary(article: ArticleDB) -> ArticleSummary | None:
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        return await summarize_article(client, article)
    finally:
        await client.close()


async def summarize_article(
    client: AsyncOpenAI,
    article: ArticleDB,
) -> ArticleSummary | None:
    try:
        response = await client.responses.parse(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Summarize the supplied news article. Write one concise summary and "
                        "at most three short key points in the article's specified language. "
                        "Do not classify, score, or add facts that are absent from the article."
                    ),
                },
                {
                    "role": "user",
                    "content": build_summary_input(article),
                },
            ],
            text_format=ArticleSummary,
        )
        return response.output_parsed
    except Exception as error:
        logger.warning("Could not summarize article %s: %s", article.id, error)
        return None


def build_summary_input(article: ArticleDB) -> str:
    return (
        f"Language: {article.language}\n"
        f"Category: {article.category}\n"
        f"Topics: {', '.join(article.topics or [])}\n"
        f"Importance: {article.importance}\n"
        f"{format_article_context(article)}"
    )
