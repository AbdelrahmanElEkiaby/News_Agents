import asyncio
import calendar
import ipaddress
import socket
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.models.source import DiscoveredFeed

COMMON_FEED_PATHS = [
    "/feed",
    "/rss",
    "/rss.xml",
    "/rss/rssfeed",
    "/feed.xml",
    "/atom.xml",
    "/news/rss",
]

METHOD_SCORES = {
    "direct": 100,
    "html_alternate": 90,
    "html_link": 75,
    "rss_directory": 65,
    "common_path": 50,
}

PREFERRED_TITLE_WORDS = [
    "all",
    "home",
    "latest",
    "headlines",
    "top stories",
    "breaking",
    "news",
    "الرئيسية",
    "أحدث",
    "آخر الأخبار",
    "عاجل",
    "أخبار",
]

MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 2_000_000
MAX_RSS_PAGES = 5
MAX_FEEDS_PER_PAGE = 20
REQUEST_TIMEOUT_SECONDS = 10.0
USER_AGENT = "NewsAgentLearningProject/1.0"


async def discover_feeds(website_url: str) -> list[DiscoveredFeed]:
    normalized_url = normalize_website_url(website_url)
    candidates: dict[str, DiscoveredFeed] = {}
    response_cache: dict[str, httpx.Response | None] = {}

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        response = await fetch_url(client, normalized_url, response_cache)

        if response is not None:
            direct_feed = parse_feed_candidate(response, "direct", normalized_url)

            if direct_feed is not None:
                return [direct_feed]

            await collect_html_candidates(
                client=client,
                response=response,
                website_url=normalized_url,
                candidates=candidates,
                response_cache=response_cache,
            )

        if not candidates:
            await collect_common_path_candidates(
                client=client,
                website_url=normalized_url,
                candidates=candidates,
                response_cache=response_cache,
            )

    return sorted(candidates.values(), key=lambda feed: feed.score, reverse=True)


async def discover_feed(website_url: str) -> str | None:
    feeds = await discover_feeds(website_url)

    if not feeds:
        return None

    return feeds[0].feed_url


async def validate_feed_url(feed_url: str) -> bool:
    normalized_url = normalize_website_url(feed_url)
    response_cache: dict[str, httpx.Response | None] = {}

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        response = await fetch_url(client, normalized_url, response_cache)

    if response is None:
        return False

    return parse_feed_candidate(response, "direct", normalized_url) is not None


async def collect_html_candidates(
    client: httpx.AsyncClient,
    response: httpx.Response,
    website_url: str,
    candidates: dict[str, DiscoveredFeed],
    response_cache: dict[str, httpx.Response | None],
) -> None:
    soup = BeautifulSoup(response.text, "html.parser")
    page_url = str(response.url)

    alternate_urls = get_alternate_feed_urls(soup, page_url)
    alternate_urls.extend(get_header_feed_urls(response, page_url))

    await collect_feed_urls(
        client=client,
        feed_urls=alternate_urls,
        method="html_alternate",
        website_url=website_url,
        candidates=candidates,
        response_cache=response_cache,
    )

    rss_page_urls = get_rss_anchor_urls(soup, page_url)

    for rss_page_url in rss_page_urls[:MAX_RSS_PAGES]:
        rss_response = await fetch_url(client, rss_page_url, response_cache)

        if rss_response is None:
            continue

        direct_feed = parse_feed_candidate(rss_response, "html_link", website_url)

        if direct_feed is not None:
            add_candidate(candidates, direct_feed)
            continue

        rss_soup = BeautifulSoup(rss_response.text, "html.parser")
        nested_urls = get_alternate_feed_urls(rss_soup, str(rss_response.url))
        nested_urls.extend(get_rss_anchor_urls(rss_soup, str(rss_response.url)))

        await collect_feed_urls(
            client=client,
            feed_urls=nested_urls[:MAX_FEEDS_PER_PAGE],
            method="rss_directory",
            website_url=website_url,
            candidates=candidates,
            response_cache=response_cache,
        )


async def collect_common_path_candidates(
    client: httpx.AsyncClient,
    website_url: str,
    candidates: dict[str, DiscoveredFeed],
    response_cache: dict[str, httpx.Response | None],
) -> None:
    parsed_url = urlparse(website_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    feed_urls = [urljoin(base_url, path) for path in COMMON_FEED_PATHS]

    await collect_feed_urls(
        client=client,
        feed_urls=feed_urls,
        method="common_path",
        website_url=website_url,
        candidates=candidates,
        response_cache=response_cache,
    )


async def collect_feed_urls(
    client: httpx.AsyncClient,
    feed_urls: list[str],
    method: str,
    website_url: str,
    candidates: dict[str, DiscoveredFeed],
    response_cache: dict[str, httpx.Response | None],
) -> None:
    async def load_candidate(feed_url: str) -> DiscoveredFeed | None:
        response = await fetch_url(client, feed_url, response_cache)

        if response is None:
            return None

        return parse_feed_candidate(response, method, website_url)

    tasks = [load_candidate(feed_url) for feed_url in unique_urls(feed_urls)]

    for candidate in await asyncio.gather(*tasks):
        if candidate is not None:
            add_candidate(candidates, candidate)


async def fetch_url(
    client: httpx.AsyncClient,
    url: str,
    response_cache: dict[str, httpx.Response | None],
) -> httpx.Response | None:
    if url in response_cache:
        return response_cache[url]

    original_url = url
    current_url = url

    for _ in range(MAX_REDIRECTS + 1):
        if not await is_safe_request_url(current_url):
            response_cache[original_url] = None
            return None

        try:
            response = await client.get(current_url)
        except httpx.HTTPError:
            response_cache[original_url] = None
            return None

        if response.is_redirect:
            location = response.headers.get("location")

            if not location:
                response_cache[original_url] = None
                return None

            current_url = urljoin(current_url, location)
            continue

        try:
            response.raise_for_status()
        except httpx.HTTPError:
            response_cache[original_url] = None
            return None

        if len(response.content) > MAX_RESPONSE_BYTES:
            response_cache[original_url] = None
            return None

        response_cache[original_url] = response
        response_cache[str(response.url)] = response
        return response

    response_cache[original_url] = None
    return None


def parse_feed_candidate(
    response: httpx.Response,
    method: str,
    website_url: str,
) -> DiscoveredFeed | None:
    parsed_feed = feedparser.parse(response.content)

    if not parsed_feed.entries:
        return None

    title = clean_text(parsed_feed.feed.get("title") or urlparse(str(response.url)).netloc)
    latest_published_at = get_latest_published_at(parsed_feed.entries)
    score = calculate_feed_score(
        method=method,
        title=title,
        item_count=len(parsed_feed.entries),
        latest_published_at=latest_published_at,
        feed_url=str(response.url),
        website_url=website_url,
    )

    return DiscoveredFeed(
        title=title,
        feed_url=str(response.url),
        feed_type=get_feed_type(parsed_feed.version),
        discovery_method=method,
        item_count=len(parsed_feed.entries),
        latest_published_at=latest_published_at,
        score=score,
    )


def calculate_feed_score(
    method: str,
    title: str,
    item_count: int,
    latest_published_at: datetime | None,
    feed_url: str,
    website_url: str,
) -> int:
    score = METHOD_SCORES.get(method, 0)
    score += min(item_count, 10)

    lowercase_title = title.lower()

    if any(word in lowercase_title for word in PREFERRED_TITLE_WORDS):
        score += 15

    if same_hostname(feed_url, website_url):
        score += 5

    if latest_published_at is not None:
        age_days = max(
            (datetime.now(timezone.utc) - latest_published_at).total_seconds() / 86400,
            0,
        )

        if age_days <= 7:
            score += 15
        elif age_days <= 30:
            score += 10
        elif age_days <= 365:
            score += 5

    return score


def get_latest_published_at(entries) -> datetime | None:
    published_dates: list[datetime] = []

    for entry in entries:
        published_time = entry.get("published_parsed") or entry.get("updated_parsed")

        if published_time is None:
            continue

        timestamp = calendar.timegm(published_time)
        published_dates.append(datetime.fromtimestamp(timestamp, tz=timezone.utc))

    if not published_dates:
        return None

    return max(published_dates)


def get_alternate_feed_urls(soup: BeautifulSoup, page_url: str) -> list[str]:
    urls: list[str] = []

    for link in soup.find_all("link"):
        rel_values = link.get("rel") or []
        type_value = (link.get("type") or "").lower()
        href = link.get("href")

        if not href or "alternate" not in rel_values:
            continue

        if type_value not in ("application/rss+xml", "application/atom+xml"):
            continue

        urls.append(urljoin(page_url, href))

    return unique_urls(urls)


def get_header_feed_urls(response: httpx.Response, page_url: str) -> list[str]:
    urls: list[str] = []

    for link_data in response.links.values():
        relation = link_data.get("rel", "")
        link_url = link_data.get("url")

        if "alternate" in relation and link_url:
            urls.append(urljoin(page_url, link_url))

    return unique_urls(urls)


def get_rss_anchor_urls(soup: BeautifulSoup, page_url: str) -> list[str]:
    urls: list[str] = []

    for link in soup.find_all("a"):
        href = link.get("href")

        if not href:
            continue

        lowercase_href = href.lower()

        if "rss" not in lowercase_href and "feed" not in lowercase_href:
            continue

        urls.append(urljoin(page_url, href))

    return unique_urls(urls)


def add_candidate(candidates: dict[str, DiscoveredFeed], candidate: DiscoveredFeed) -> None:
    existing_candidate = candidates.get(candidate.feed_url)

    if existing_candidate is None or candidate.score > existing_candidate.score:
        candidates[candidate.feed_url] = candidate


def unique_urls(urls: list[str]) -> list[str]:
    return list(dict.fromkeys(urls))


def normalize_website_url(url: str) -> str:
    cleaned_url = url.strip()

    if not cleaned_url.startswith(("http://", "https://")):
        cleaned_url = f"https://{cleaned_url}"

    return cleaned_url


def is_safe_http_url(url: str) -> bool:
    parsed_url = urlparse(url)

    if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
        return False

    if parsed_url.username or parsed_url.password:
        return False

    hostname = parsed_url.hostname.lower()

    if hostname == "localhost" or hostname.endswith((".localhost", ".local")):
        return False

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True

    return address.is_global


async def is_safe_request_url(url: str) -> bool:
    if not is_safe_http_url(url):
        return False

    hostname = urlparse(url).hostname

    if hostname is None:
        return False

    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        pass

    try:
        address_info = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
    except socket.gaierror:
        return False

    addresses = {item[4][0] for item in address_info}

    return bool(addresses) and all(ipaddress.ip_address(address).is_global for address in addresses)


def same_hostname(first_url: str, second_url: str) -> bool:
    first_hostname = (urlparse(first_url).hostname or "").removeprefix("www.")
    second_hostname = (urlparse(second_url).hostname or "").removeprefix("www.")
    return first_hostname == second_hostname


def get_feed_type(version: str) -> str:
    if "atom" in (version or "").lower():
        return "atom"

    return "rss"


def clean_text(value: str) -> str:
    return " ".join(value.split())
