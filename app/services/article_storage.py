from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.article_db import ArticleDB


def save_new_articles(db: Session, articles: list[Article]) -> tuple[dict[str, int], list[ArticleDB]]:
    saved_count = 0
    duplicate_count = 0
    content_updated_count = 0
    saved_urls: set[str] = set()
    saved_articles: list[ArticleDB] = []

    for article in articles:
        if article.url in saved_urls:
            duplicate_count += 1
            continue

        existing_article = db.query(ArticleDB).filter(ArticleDB.url == article.url).first()

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
        saved_urls.add(article.url)
        saved_count += 1

    db.commit()

    stats = {
        "fetched": len(articles),
        "saved": saved_count,
        "duplicates": duplicate_count,
        "content_updated": content_updated_count,
    }

    return stats, saved_articles


def save_article_classification(db: Session, article: ArticleDB, category: str, topics: list[str]) -> None:
    article.category = category
    article.topics = topics
    db.commit()
    db.refresh(article)


def save_article_summary(db: Session, article: ArticleDB, summary: str, key_points: list[str]) -> None:
    article.summary = summary
    article.key_points = key_points
    db.commit()
    db.refresh(article)


def get_articles(db: Session) -> list[ArticleDB]:
    return db.query(ArticleDB).order_by(ArticleDB.published_at.desc().nullslast()).all()


def get_article_by_id(db: Session, article_id: int) -> ArticleDB | None:
    return db.query(ArticleDB).filter(ArticleDB.id == article_id).first()
