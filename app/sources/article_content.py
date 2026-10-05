import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

from app.models.article_db import ArticleDB

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 6000
MIN_PARAGRAPH_LENGTH = 40


async def fetch_article_content(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as error:
        logger.warning("Could not fetch article content from %s: %s", url, error)
        return None

    return extract_text_from_html(response.text)


async def fetch_article_contents(
    articles: list[ArticleDB],
    max_concurrency: int = 5,
) -> dict[int, str]:
    if not articles:
        return {}

    semaphore = asyncio.Semaphore(max_concurrency)

    async with httpx.AsyncClient(
        timeout=10.0,
        follow_redirects=True,
        headers={"User-Agent": "NewsAgentLearningProject/1.0"},
    ) as client:

        async def fetch_one(article: ArticleDB) -> tuple[int, str | None]:
            async with semaphore:
                content = await fetch_article_content(client, article.url)
                return article.id, content

        results = await asyncio.gather(*(fetch_one(article) for article in articles))

    return {article_id: content for article_id, content in results if content}


def extract_text_from_html(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()

    container = soup.find("article") or soup.find("main") or soup.body

    if container is None:
        return None

    paragraphs = []

    for paragraph in container.find_all("p"):
        text = clean_text(paragraph.get_text(" "))

        if len(text) >= MIN_PARAGRAPH_LENGTH:
            paragraphs.append(text)

    content = join_unique_paragraphs(paragraphs)

    if not content:
        return None

    return content[:MAX_CONTENT_LENGTH]


def extract_text_from_feed_html(html: str) -> str | None:
    text = clean_text(BeautifulSoup(html, "html.parser").get_text(" "))

    if len(text) < MIN_PARAGRAPH_LENGTH:
        return None

    return text[:MAX_CONTENT_LENGTH]


def join_unique_paragraphs(paragraphs: list[str]) -> str:
    unique_paragraphs = []
    seen_paragraphs = set()

    for paragraph in paragraphs:
        if paragraph in seen_paragraphs:
            continue

        seen_paragraphs.add(paragraph)
        unique_paragraphs.append(paragraph)

    return "\n\n".join(unique_paragraphs)


def clean_text(value: str) -> str:
    return " ".join(value.split())
