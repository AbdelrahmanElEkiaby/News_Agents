from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global engine

    if engine is None:
        database_url = make_url(settings.database_url)

        if database_url.drivername == "postgresql":
            database_url = database_url.set(drivername="postgresql+psycopg")

        engine = create_engine(database_url)

    return engine


def get_session_local() -> sessionmaker[Session]:
    global SessionLocal

    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

    return SessionLocal


def create_database_tables() -> None:
    import app.models.article_db

    Base.metadata.create_all(bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    session_local = get_session_local()
    db = session_local()

    try:
        yield db
    finally:
        db.close()
