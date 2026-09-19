from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import create_database_tables, get_db
from app.models.article import ArticleFetchResult, ArticleRead
from app.services.article_classification import classify_article
from app.services.article_storage import (
    get_article_by_id,
    get_articles,
    save_article_classification,
    save_article_summary,
    save_new_articles,
)
from app.services.article_summarization import summarize_article
from app.services.news_collection import fetch_all_articles

app = FastAPI(title="News Agent API")
app.state.settings = settings


@app.on_event("startup")
def startup():
    create_database_tables()


@app.get("/")
async def read_root():
    return {"message": "News Agent API is running"}


@app.post("/articles/fetch", response_model=ArticleFetchResult)
async def fetch_and_save_articles(db: Session = Depends(get_db)):
    articles = await fetch_all_articles()
    stats, saved_articles = save_new_articles(db, articles)

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

    return {
        **stats,
        "classified": classified_count,
        "summarized": summarized_count,
    }


@app.get("/articles", response_model=list[ArticleRead])
def list_articles(db: Session = Depends(get_db)):
    return get_articles(db)


@app.get("/articles/{article_id}", response_model=ArticleRead)
def read_article(article_id: int, db: Session = Depends(get_db)):
    article = get_article_by_id(db, article_id)

    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    return article
