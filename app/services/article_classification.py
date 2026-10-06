import asyncio
import logging
from collections.abc import Mapping
from typing import Protocol

from typesafe_sdk import AsyncTypeSafeClient, Choice

from app.config import settings
from app.models.article import ArticleDB
from app.schemas.article import ArticleClassification
from app.services.article_context import build_article_context

logger = logging.getLogger(__name__)

CATEGORY_CRITERIA: Mapping[str, str] = {
    "ai": "Artificial intelligence, machine learning, models, or AI products.",
    "technology": "General technology, hardware, internet services, or consumer tech.",
    "business": "Companies, industries, management, deals, or corporate activity.",
    "economy": "Macroeconomics, trade, employment, inflation, or economic policy.",
    "politics": "Elections, parties, politicians, legislation, or domestic politics.",
    "middle_east": "News primarily concerning the Middle East or North Africa.",
    "world": "International news that is not primarily about the Middle East.",
    "science": "Scientific research, discoveries, space, climate, or environment.",
    "health": "Medicine, public health, healthcare, wellness, or disease.",
    "sports": "Sporting events, teams, athletes, or competitions.",
    "entertainment": "Film, television, music, celebrities, arts, or culture.",
    "other": "None of the other categories is a good fit.",
}

TOPIC_CRITERIA: Mapping[str, str] = {
    "artificial_intelligence": "AI systems, models, research, policy, or products.",
    "software": "Software products, development, platforms, apps, or cloud services.",
    "startups": "Startups, venture capital, founders, or early-stage businesses.",
    "cybersecurity": "Security incidents, privacy, malware, vulnerabilities, or defence.",
    "finance": "Banking, investment, personal finance, or financial institutions.",
    "markets": "Stocks, commodities, currencies, market movements, or trading.",
    "government": "Government administration, public policy, elections, or legislation.",
    "geopolitics": "International relations, conflict, diplomacy, or national strategy.",
    "middle_east": "People, countries, conflict, politics, or business in the Middle East.",
    "science": "Scientific research, space, climate, nature, or discoveries.",
    "health": "Medicine, healthcare, public health, wellness, or disease.",
    "football": "Association football teams, players, leagues, or matches.",
    "other": "None of the other topics is a good fit.",
}

LANGUAGE_CRITERIA: Mapping[str, str] = {
    "ar": "The article is primarily written in Arabic.",
    "en": "The article is primarily written in English.",
    "other": "The article is primarily written in another language or is unclear.",
}

IMPORTANCE_CRITERIA: Mapping[str, str] = {
    "low": "Minor, routine, local, or low-impact news.",
    "medium": "Notable news with a limited or moderate impact.",
    "high": "Major news with broad public, economic, political, or social impact.",
    "critical": "Urgent, exceptional news with immediate and very broad consequences.",
}

IMPORTANCE_SCORES = {
    "low": 0.0,
    "medium": 1 / 3,
    "high": 2 / 3,
    "critical": 1.0,
}


class ChoiceAnswer(Protocol):
    choice: str
    confidence: float


async def classify_articles(
    articles: list[ArticleDB],
    max_concurrency: int = 3,
) -> list[tuple[ArticleDB, ArticleClassification]]:
    if not articles:
        return []

    if not settings.jev_api_key:
        logger.warning("Skipping article classification because JEV_API_KEY is not set")
        return []

    semaphore = asyncio.Semaphore(max_concurrency)

    async with AsyncTypeSafeClient(
        api_key=settings.jev_api_key,
        model=settings.jev_model,
    ) as client:

        async def classify_one(
            article: ArticleDB,
        ) -> tuple[ArticleDB, ArticleClassification] | None:
            async with semaphore:
                classification = await classify_article(client, article)

            if classification is None:
                return None

            return article, classification

        results = await asyncio.gather(*(classify_one(article) for article in articles))

    return [result for result in results if result is not None]


async def classify_article(
    client: AsyncTypeSafeClient,
    article: ArticleDB,
) -> ArticleClassification | None:
    try:
        response = await client.system_one(
            state=build_article_context(article),
            questions={
                "language": Choice(
                    instructions="Identify the primary language of the article.",
                    criteria=LANGUAGE_CRITERIA,
                ),
                "category": Choice(
                    instructions="Choose the single best category for the article.",
                    criteria=CATEGORY_CRITERIA,
                ),
                "primary_topic": Choice(
                    instructions="Choose the single most important topic in the article.",
                    criteria=TOPIC_CRITERIA,
                ),
                "secondary_topic": Choice(
                    instructions=(
                        "Choose a useful secondary topic distinct from the main topic, "
                        "or none when no second topic clearly applies."
                    ),
                    criteria={**TOPIC_CRITERIA, "none": "No clear secondary topic applies."},
                ),
                "importance": Choice(
                    instructions=(
                        "Judge the article's overall news importance using impact, urgency, "
                        "and breadth of consequences."
                    ),
                    criteria=IMPORTANCE_CRITERIA,
                ),
            },
        )

        answers = response.choices
        _require_answers(answers)

        primary_topic = answers["primary_topic"].choice
        secondary_topic = answers["secondary_topic"].choice
        if secondary_topic == primary_topic:
            secondary_topic = "none"

        importance = answers["importance"].choice
        confidence = min(answer.confidence for answer in answers.values())

        return ArticleClassification(
            language=answers["language"].choice,
            category=answers["category"].choice,
            primary_topic=primary_topic,
            secondary_topic=secondary_topic,
            importance=importance,
            importance_score=IMPORTANCE_SCORES[importance],
            confidence=confidence,
        )
    except Exception as error:
        logger.warning("Could not classify article %s with Jev: %s", article.id, error)
        return None


def _require_answers(answers: Mapping[str, ChoiceAnswer]) -> None:
    expected = {"language", "category", "primary_topic", "secondary_topic", "importance"}
    missing = expected.difference(answers)
    if missing:
        raise ValueError(f"Jev response is missing answers: {', '.join(sorted(missing))}")
