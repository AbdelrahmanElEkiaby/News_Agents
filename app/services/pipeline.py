import logging

from sqlalchemy.orm import Session

from app.services.article_classification import classify_article
from app.services.article_storage import (
    save_article_classification,
    save_article_summary,
    save_new_articles,
)
from app.services.article_summarization import summarize_article
from app.services.news_collection import fetch_all_articles

logger = logging.getLogger(__name__)


async def run_news_pipeline(db: Session) -> dict[str, int]:
    logger.info("Fetching articles...")
    articles = await fetch_all_articles()
    logger.info("%s articles received.", len(articles))

    stats, saved_articles = save_new_articles(db, articles)
    logger.info("%s new articles saved.", stats["saved"])
    logger.info("%s duplicate articles skipped.", stats["duplicates"])

    classified_count = 0
    summarized_count = 0

    for article in saved_articles:
        classification = await classify_article(article)

        if classification is not None:
            save_article_classification(
                db=db,
                article=article,
                category=classification.category,
                topics=classification.topics,
            )
            classified_count += 1

        summary = await summarize_article(article)

        if summary is not None:
            save_article_summary(
                db=db,
                article=article,
                summary=summary.summary,
                key_points=summary.key_points,
            )
            summarized_count += 1

    logger.info("%s articles classified.", classified_count)
    logger.info("%s articles summarized.", summarized_count)
    logger.info("Pipeline completed.")

    return {
        **stats,
        "classified": classified_count,
        "summarized": summarized_count,
    }
