import logging
from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.config import settings
from app.models.article import ArticleDB
from app.schemas.article import ArticleRelevance, FeedArticle, Preferences

logger = logging.getLogger(__name__)


async def build_personalized_feed(
    articles: list[ArticleDB],
    preferences: Preferences,
    max_articles: int,
) -> list[FeedArticle]:
    candidate_articles = filter_articles_by_language(articles, preferences.languages)
    candidate_articles = candidate_articles[:max_articles]

    feed_articles = []

    for article in candidate_articles:
        ai_result = await calculate_ai_relevance(article, preferences)
        freshness_score = calculate_freshness_score(article)
        topic_match_score = calculate_topic_match_score(article, preferences)

        final_score = calculate_final_score(
            ai_relevance=ai_result.relevance_score,
            freshness_score=freshness_score,
            topic_match_score=topic_match_score,
        )

        feed_articles.append(
            FeedArticle(
                id=article.id,
                source_id=article.source_id,
                title=article.title,
                url=article.url,
                source=article.source,
                language=article.language,
                summary=article.summary,
                category=article.category,
                topics=article.topics,
                published_at=article.published_at,
                score=round(final_score, 4),
                ai_relevance=round(ai_result.relevance_score, 4),
                freshness_score=round(freshness_score, 4),
                topic_match_score=round(topic_match_score, 4),
                reason=ai_result.reason,
            )
        )

    return sorted(feed_articles, key=lambda article: article.score, reverse=True)


async def calculate_ai_relevance(article: ArticleDB, preferences: Preferences) -> ArticleRelevance:
    if not settings.openai_api_key:
        return ArticleRelevance(
            relevance_score=0.0,
            reason="OPENAI_API_KEY is not set, so AI relevance was skipped.",
        )

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        response = await client.responses.parse(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Decide how relevant a news article is to the reader's preferences. "
                        "Return a score from 0.0 to 1.0 and one short reason."
                    ),
                },
                {
                    "role": "user",
                    "content": build_relevance_prompt(article, preferences),
                },
            ],
            text_format=ArticleRelevance,
        )

        return response.output_parsed
    except Exception as error:
        logger.warning("Could not calculate AI relevance for article %s: %s", article.id, error)
        return ArticleRelevance(
            relevance_score=0.0,
            reason="AI relevance failed for this article.",
        )


def build_relevance_prompt(article: ArticleDB, preferences: Preferences) -> str:
    return (
        f"Reader topics: {preferences.topics}\n"
        f"Reader languages: {preferences.languages}\n\n"
        f"Article title: {article.title}\n"
        f"Article language: {article.language or 'unknown'}\n"
        f"Article source: {article.source}\n"
        f"Article category: {article.category or 'unknown'}\n"
        f"Article topics: {article.topics or []}\n"
        f"Article summary: {article.summary or ''}\n"
        f"Article description: {article.description or ''}"
    )


def filter_articles_by_language(articles: list[ArticleDB], languages: list[str]) -> list[ArticleDB]:
    if not languages:
        return articles

    allowed_languages = {language.lower() for language in languages}

    return [
        article
        for article in articles
        if article.language is None or article.language.lower() in allowed_languages
    ]


def calculate_freshness_score(article: ArticleDB) -> float:
    if article.published_at is None:
        return 0.2

    published_at = article.published_at

    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    age = datetime.now(timezone.utc) - published_at
    age_days = max(age.total_seconds() / 86400, 0)

    if age_days <= 1:
        return 1.0

    if age_days <= 3:
        return 0.8

    if age_days <= 7:
        return 0.6

    if age_days <= 30:
        return 0.3

    return 0.1


def calculate_topic_match_score(article: ArticleDB, preferences: Preferences) -> float:
    if not preferences.topics:
        return 0.0

    article_text = " ".join(
        [
            article.title or "",
            article.category or "",
            article.summary or "",
            " ".join(article.topics or []),
        ]
    ).lower()

    matched_topics = 0

    for topic in preferences.topics:
        if topic.lower() in article_text:
            matched_topics += 1

    return matched_topics / len(preferences.topics)


def calculate_final_score(
    ai_relevance: float,
    freshness_score: float,
    topic_match_score: float,
) -> float:
    return (
        ai_relevance * 0.60
        + freshness_score * 0.25
        + topic_match_score * 0.15
    )
