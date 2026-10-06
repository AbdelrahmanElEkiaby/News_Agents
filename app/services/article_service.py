from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.article import ArticleDB
from app.models.user import UserSourceDB
from app.schemas.article import Article, ArticleClassification


def save_new_articles(
    db: Session,
    articles: list[Article],
) -> tuple[dict[str, int], list[ArticleDB]]:
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
            if existing_article.source_id is None and article.source_id is not None:
                existing_article.source_id = article.source_id

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

    return {
        "fetched": len(articles),
        "saved": saved_count,
        "duplicates": duplicate_count,
        "content_updated": content_updated_count,
    }, saved_articles


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


def get_articles_missing_classification(
    db: Session,
    limit: int = 100,
    source_ids: set[int] | None = None,
) -> list[ArticleDB]:
    query = db.query(ArticleDB).filter(
        or_(
            ArticleDB.language.is_(None),
            ArticleDB.category.is_(None),
            ArticleDB.topics.is_(None),
            ArticleDB.importance.is_(None),
            ArticleDB.importance_score.is_(None),
            ArticleDB.classification_confidence.is_(None),
        )
    )

    if source_ids is not None:
        query = query.filter(ArticleDB.source_id.in_(source_ids))

    return (
        query
        .order_by(ArticleDB.created_at.asc())
        .limit(limit)
        .all()
    )


def save_article_classifications(
    db: Session,
    classifications: list[tuple[ArticleDB, ArticleClassification]],
) -> int:
    for article, classification in classifications:
        topics = [classification.primary_topic]
        if classification.secondary_topic != "none":
            topics.append(classification.secondary_topic)

        article.language = classification.language
        article.category = classification.category
        article.topics = topics
        article.importance = classification.importance
        article.importance_score = classification.importance_score
        article.classification_confidence = classification.confidence

    db.commit()
    return len(classifications)


def get_articles_for_user(db: Session, user_id: int) -> list[ArticleDB]:
    source_ids = select(UserSourceDB.source_id).where(UserSourceDB.user_id == user_id)
    return (
        db.query(ArticleDB)
        .filter(ArticleDB.source_id.in_(source_ids))
        .order_by(ArticleDB.published_at.desc().nullslast())
        .all()
    )


def get_article_by_id(db: Session, article_id: int) -> ArticleDB | None:
    return db.query(ArticleDB).filter(ArticleDB.id == article_id).first()
