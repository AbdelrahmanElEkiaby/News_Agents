import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import get_session_local
from app.services.news_pipeline import run_news_pipeline

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> AsyncIOScheduler:
    global scheduler

    if scheduler is not None and scheduler.running:
        return scheduler

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_news_fetch,
        "interval",
        minutes=settings.news_fetch_interval_minutes,
        id="news_fetch_job",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    logger.info(
        "News fetch scheduler started. Interval: %s minutes.",
        settings.news_fetch_interval_minutes,
    )

    return scheduler


def stop_scheduler() -> None:
    global scheduler

    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("News fetch scheduler stopped.")


async def scheduled_news_fetch() -> None:
    session_local = get_session_local()
    db = session_local()

    try:
        await run_news_pipeline(db)
    except Exception as error:
        logger.exception("Scheduled news pipeline failed: %s", error)
    finally:
        db.close()
