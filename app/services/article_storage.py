from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.article import Article, ArticleAnalysis
from app.models.article_db import ArticleDB


def save_new_articles(db: Session, articles: list[Article]) -> tuple[dict[str, int], list[ArticleDB]]:
    saved_count = 0
    duplicate_count = 0
    content_updated_count = 0
    saved_articles: list[ArticleDB] = []
    unique_articles: list[Article] = []
    incoming_urls: set[str] = set()

    for article in articles:
        if article.url in incoming_urls:
            duplicate_count += 1
            continue

        incoming_urls.add(article.url)
        unique_articles.append(article)

    existing_by_url: dict[str, ArticleDB] = {}

    if incoming_urls:
        existing_articles = db.query(ArticleDB).filter(ArticleDB.url.in_(incoming_urls)).all()
        existing_by_url = {article.url: article for article in existing_articles}

    for article in unique_articles:
        existing_article = existing_by_url.get(article.url)

        if existing_article is not None:
            if not existing_article.content and article.content:
                existing_article.content = article.content
                content_updated_count += 1

            duplicate_count += 1
            continue

        db_article = ArticleDB(**article.model_dump())
        db.add(db_article)
        db.flush()
        saved_articles.append(db_article)
        saved_count += 1

    db.commit()

    stats = {
        "fetched": len(articles),
        "saved": saved_count,
        "duplicates": duplicate_count,
        "content_updated": content_updated_count,
    }

    return stats, saved_articles


def save_article_contents(db: Session, contents: dict[int, str]) -> int:
    if not contents:
        return 0

    articles = db.query(ArticleDB).filter(ArticleDB.id.in_(contents)).all()
    updated_count = 0

    for article in articles:
        if article.content:
            continue

        article.content = contents[article.id]
        updated_count += 1

    db.commit()
    return updated_count


def get_articles_missing_analysis(db: Session, limit: int = 100) -> list[ArticleDB]:
    return (
        db.query(ArticleDB)
        .filter(
            or_(
                ArticleDB.category.is_(None),
                ArticleDB.topics.is_(None),
                ArticleDB.summary.is_(None),
                ArticleDB.key_points.is_(None),
            )
        )
        .order_by(ArticleDB.created_at.asc())
        .limit(limit)
        .all()
    )


def save_article_analyses(
    db: Session,
    analyses: list[tuple[ArticleDB, ArticleAnalysis]],
) -> tuple[int, int]:
    classified_count = 0
    summarized_count = 0

    for article, analysis in analyses:
        if article.category is None or article.topics is None:
            classified_count += 1

        if article.summary is None or article.key_points is None:
            summarized_count += 1

        article.language = analysis.language
        article.category = analysis.category
        article.topics = analysis.topics
        article.summary = analysis.summary
        article.key_points = analysis.key_points

    db.commit()
    return classified_count, summarized_count


def get_articles(db: Session) -> list[ArticleDB]:
    return db.query(ArticleDB).order_by(ArticleDB.published_at.desc().nullslast()).all()


def get_article_by_id(db: Session, article_id: int) -> ArticleDB | None:
    return db.query(ArticleDB).filter(ArticleDB.id == article_id).first()
