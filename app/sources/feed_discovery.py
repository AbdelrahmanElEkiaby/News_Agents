from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

COMMON_FEED_PATHS = [
    "/feed",
    "/rss",
    "/rss.xml",
    "/feed.xml",
    "/atom.xml",
    "/news/rss",
]


async def discover_feed(website_url: str) -> str | None:
    normalized_url = normalize_website_url(website_url)

    async with httpx.AsyncClient(
        timeout=10.0,
        follow_redirects=True,
        headers={"User-Agent": "NewsAgentLearningProject/1.0"},
    ) as client:
        feed_url = await discover_feed_from_html(client, normalized_url)

        if feed_url is not None:
            return feed_url

        return await discover_feed_from_common_paths(client, normalized_url)


def normalize_website_url(url: str) -> str:
    cleaned_url = url.strip()

    if not cleaned_url.startswith(("http://", "https://")):
        cleaned_url = f"https://{cleaned_url}"

    return cleaned_url


async def discover_feed_from_html(client: httpx.AsyncClient, website_url: str) -> str | None:
    try:
        response = await client.get(website_url)
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    for link in soup.find_all("link"):
        rel_values = link.get("rel") or []
        type_value = (link.get("type") or "").lower()
        href = link.get("href")

        if not href:
            continue

        if "alternate" not in rel_values:
            continue

        if type_value not in ("application/rss+xml", "application/atom+xml"):
            continue

        feed_url = urljoin(str(response.url), href)

        if await is_valid_feed(client, feed_url):
            return feed_url

    return None


async def discover_feed_from_common_paths(client: httpx.AsyncClient, website_url: str) -> str | None:
    parsed_url = urlparse(website_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    for path in COMMON_FEED_PATHS:
        feed_url = urljoin(base_url, path)

        if await is_valid_feed(client, feed_url):
            return feed_url

    return None


async def is_valid_feed(client: httpx.AsyncClient, feed_url: str) -> bool:
    try:
        response = await client.get(feed_url)
        response.raise_for_status()
    except httpx.HTTPError:
        return False

    parsed_feed = feedparser.parse(response.content)
    return len(parsed_feed.entries) > 0
