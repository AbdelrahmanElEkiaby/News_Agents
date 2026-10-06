from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.source import SourceDB
from app.schemas.source import SourceCreate, SourceUpdate


def get_sources(db: Session) -> list[SourceDB]:
    return db.query(SourceDB).order_by(SourceDB.id.asc()).all()


def get_active_sources(db: Session) -> list[SourceDB]:
    return (
        db.query(SourceDB)
        .filter(SourceDB.is_active.is_(True))
        .order_by(SourceDB.id.asc())
        .all()
    )


def get_source_by_id(db: Session, source_id: int) -> SourceDB | None:
    return db.query(SourceDB).filter(SourceDB.id == source_id).first()


def get_source_by_feed_url(db: Session, feed_url: str | None) -> SourceDB | None:
    if not feed_url:
        return None

    return db.query(SourceDB).filter(SourceDB.feed_url == feed_url).first()


def create_source(
    db: Session,
    source_data: SourceCreate,
    owner_user_id: int,
) -> SourceDB:
    source = SourceDB(
        owner_user_id=owner_user_id,
        name=source_data.name,
        website_url=source_data.website_url,
        feed_url=source_data.feed_url,
        language=source_data.language,
        source_type=source_data.source_type,
        is_active=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def update_source(db: Session, source: SourceDB, source_data: SourceUpdate) -> SourceDB:
    update_data = source_data.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(source, field_name, value)

    db.commit()
    db.refresh(source)
    return source


def disable_source(db: Session, source: SourceDB) -> SourceDB:
    source.is_active = False
    db.commit()
    db.refresh(source)
    return source


def mark_source_fetch_started(db: Session, source: SourceDB) -> None:
    source.last_fetched_at = datetime.now(timezone.utc)
    db.commit()


def mark_source_fetch_success(db: Session, source: SourceDB) -> None:
    source.last_success_at = datetime.now(timezone.utc)
    source.last_error = None
    db.commit()


def mark_source_fetch_error(db: Session, source: SourceDB, error: BaseException) -> None:
    source.last_error = str(error)[:500]
    db.commit()
