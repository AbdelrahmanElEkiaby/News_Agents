from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.source import (
    SourceCreate,
    SourceDiscoverRequest,
    SourceDiscoverResponse,
    SourceRead,
    SourceUpdate,
    SourceWebsiteCreate,
)
from app.services.auth_service import get_current_user
from app.services.source_service import (
    create_source,
    disable_source,
    get_source_by_feed_url,
    get_source_by_id,
    get_sources,
    update_source,
)
from app.services.feed_discovery import discover_feeds, normalize_website_url, validate_feed_url

router = APIRouter(
    prefix="/sources",
    tags=["sources"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[SourceRead])
def list_sources(db: Session = Depends(get_db)):
    return get_sources(db)


@router.post("/discover", response_model=SourceDiscoverResponse)
async def discover_source(source_data: SourceDiscoverRequest):
    website_url = normalize_website_url(source_data.url)
    feeds = await discover_feeds(website_url)

    if not feeds:
        return SourceDiscoverResponse(
            website_url=website_url,
            feed_url=None,
            feed_found=False,
            message="No RSS or Atom feed found.",
            feeds=[],
            recommended_feed=None,
        )

    recommended_feed = feeds[0]
    return SourceDiscoverResponse(
        website_url=website_url,
        feed_url=recommended_feed.feed_url,
        feed_found=True,
        message=f"Found {len(feeds)} RSS or Atom feed(s).",
        feeds=feeds,
        recommended_feed=recommended_feed.feed_url,
    )


@router.post("/from-website", response_model=SourceRead)
async def create_source_from_website(
    source_data: SourceWebsiteCreate,
    db: Session = Depends(get_db),
):
    website_url = normalize_website_url(source_data.url)
    feeds = await discover_feeds(website_url)

    if not feeds:
        raise HTTPException(status_code=400, detail="No RSS or Atom feed found.")

    recommended_feed = feeds[0]

    if get_source_by_feed_url(db, recommended_feed.feed_url) is not None:
        raise HTTPException(status_code=400, detail="A source with this feed URL already exists")

    source_name = source_data.name or recommended_feed.title or get_name_from_url(website_url)
    return create_source(
        db,
        SourceCreate(
            name=source_name,
            website_url=website_url,
            feed_url=recommended_feed.feed_url,
            language=source_data.language,
        ),
    )


@router.get("/{source_id}", response_model=SourceRead)
def read_source(source_id: int, db: Session = Depends(get_db)):
    source = get_source_by_id(db, source_id)

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    return source


@router.post("", response_model=SourceRead)
async def create_new_source(source_data: SourceCreate, db: Session = Depends(get_db)):
    feed_url = normalize_website_url(source_data.feed_url or "")

    if not await validate_feed_url(feed_url):
        raise HTTPException(status_code=400, detail="The RSS or Atom feed URL is not valid")

    source_data.feed_url = feed_url

    if get_source_by_feed_url(db, feed_url) is not None:
        raise HTTPException(status_code=400, detail="A source with this feed URL already exists")

    return create_source(db, source_data)


@router.patch("/{source_id}", response_model=SourceRead)
async def update_existing_source(
    source_id: int,
    source_data: SourceUpdate,
    db: Session = Depends(get_db),
):
    source = get_source_by_id(db, source_id)

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    updated_feed_url = source.feed_url

    if "feed_url" in source_data.model_fields_set:
        updated_feed_url = source_data.feed_url

    if not updated_feed_url:
        raise HTTPException(status_code=400, detail="feed_url is required for RSS sources")

    normalized_feed_url = normalize_website_url(updated_feed_url)

    if normalized_feed_url != source.feed_url:
        if not await validate_feed_url(normalized_feed_url):
            raise HTTPException(status_code=400, detail="The RSS or Atom feed URL is not valid")

        if get_source_by_feed_url(db, normalized_feed_url) is not None:
            raise HTTPException(status_code=400, detail="A source with this feed URL already exists")

    source_data.feed_url = normalized_feed_url
    return update_source(db, source, source_data)


@router.delete("/{source_id}", response_model=SourceRead)
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = get_source_by_id(db, source_id)

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    return disable_source(db, source)


def get_name_from_url(url: str) -> str:
    hostname = urlparse(url).netloc.replace("www.", "")
    return hostname.split(":")[0] if hostname else "New Source"
