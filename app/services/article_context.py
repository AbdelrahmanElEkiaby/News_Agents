from app.models.article import ArticleDB


def build_article_context(article: ArticleDB, content_limit: int = 3000) -> dict[str, str]:
    """Return the compact article data shared with external AI services."""
    return {
        "title": article.title,
        "description": article.description or "",
        "content": (article.content or "")[:content_limit],
        "source": article.source,
    }


def format_article_context(article: ArticleDB, content_limit: int = 3000) -> str:
    context = build_article_context(article, content_limit=content_limit)
    return "\n".join(f"{key.title()}: {value}" for key, value in context.items())
