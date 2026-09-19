from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.article_db import ArticleDB


def save_new_articles(db: Session, articles: list[Article]) -> dict[str, int]:
    saved_count = 0
    duplicate_count = 0
    saved_urls: set[str] = set()

    for article in articles:
        if article.url in saved_urls:
            duplicate_count += 1
            continue

        existing_article = db.query(ArticleDB).filter(ArticleDB.url == article.url).first()

        if existing_article is not None:
            duplicate_count += 1
            continue

        db_article = ArticleDB(**article.model_dump())
        db.add(db_article)
        saved_urls.add(article.url)
        saved_count += 1

    db.commit()

    return {
        "fetched": len(articles),
        "saved": saved_count,
        "duplicates": duplicate_count,
    }


def get_articles(db: Session) -> list[ArticleDB]:
    return db.query(ArticleDB).order_by(ArticleDB.published_at.desc().nullslast()).all()


def get_article_by_id(db: Session, article_id: int) -> ArticleDB | None:
    return db.query(ArticleDB).filter(ArticleDB.id == article_id).first()
