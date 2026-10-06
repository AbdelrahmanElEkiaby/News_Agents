from collections.abc import Generator

from sqlalchemy import create_engine, text
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
    import app.models.article
    import app.models.source
    import app.models.user

    Base.metadata.create_all(bind=get_engine())
    add_missing_article_columns()
    add_missing_source_columns()
    add_missing_user_columns()
    backfill_article_source_ids()


def add_missing_article_columns() -> None:
    with get_engine().begin() as connection:
        connection.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS category VARCHAR"))
        connection.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS topics JSON"))
        connection.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary TEXT"))
        connection.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS key_points JSON"))
        connection.execute(
            text(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS "
                "summary_status VARCHAR DEFAULT 'not_requested'"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS "
                "summary_requested_at TIMESTAMP WITH TIME ZONE"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS "
                "summary_requested_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_articles_summary_requested_by_user_id "
                "ON articles (summary_requested_by_user_id)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS "
                "summary_generated_at TIMESTAMP WITH TIME ZONE"
            )
        )
        connection.execute(
            text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary_error TEXT")
        )
        connection.execute(
            text(
                "UPDATE articles SET summary_status = 'completed', "
                "summary_generated_at = COALESCE(summary_generated_at, created_at) "
                "WHERE summary IS NOT NULL AND summary_status <> 'completed'"
            )
        )
        connection.execute(
            text(
                "UPDATE articles SET summary_status = 'not_requested' "
                "WHERE summary IS NULL AND summary_status IS NULL"
            )
        )
        connection.execute(
            text("ALTER TABLE articles ALTER COLUMN summary_status SET DEFAULT 'not_requested'")
        )
        connection.execute(
            text("ALTER TABLE articles ALTER COLUMN summary_status SET NOT NULL")
        )
        connection.execute(text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS importance VARCHAR"))
        connection.execute(
            text("ALTER TABLE articles ADD COLUMN IF NOT EXISTS importance_score DOUBLE PRECISION")
        )
        connection.execute(
            text(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS "
                "classification_confidence DOUBLE PRECISION"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE articles ADD COLUMN IF NOT EXISTS source_id INTEGER "
                "REFERENCES sources(id)"
            )
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_articles_source_id ON articles (source_id)")
        )


def add_missing_source_columns() -> None:
    with get_engine().begin() as connection:
        connection.execute(text("ALTER TABLE sources ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true"))
        connection.execute(text("ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_fetched_at TIMESTAMP WITH TIME ZONE"))
        connection.execute(text("ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_success_at TIMESTAMP WITH TIME ZONE"))
        connection.execute(text("ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_error TEXT"))
        connection.execute(text("ALTER TABLE sources ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now()"))


def add_missing_user_columns() -> None:
    with get_engine().begin() as connection:
        connection.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_name_key"))
        connection.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR"))
        connection.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR")
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_lower "
                "ON users (lower(email))"
            )
        )


def backfill_article_source_ids() -> None:
    with get_engine().begin() as connection:
        connection.execute(
            text(
                "UPDATE articles SET source_id = sources.id FROM sources "
                "WHERE articles.source_id IS NULL "
                "AND lower(articles.source) = lower(sources.name)"
            )
        )


def get_db() -> Generator[Session, None, None]:
    session_local = get_session_local()
    db = session_local()

    try:
        yield db
    finally:
        db.close()
