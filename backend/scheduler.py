"""APScheduler — twice-daily collection runs."""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import Settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def setup_scheduler(settings: Settings) -> None:
    """Register collection jobs for each configured time."""
    if scheduler.running:
        return

    from pipeline.orchestrator import run_pipeline

    for time_str in settings.schedule_times:
        hour, minute = map(int, time_str.split(":"))
        scheduler.add_job(
            lambda: asyncio.create_task(_run_all_categories(settings, run_pipeline)),
            CronTrigger(hour=hour, minute=minute, timezone=settings.schedule_timezone),
            id=f"collect_{time_str}",
            replace_existing=True,
        )
        logger.info("Scheduled collection at %s %s", time_str, settings.schedule_timezone)

    scheduler.start()
    logger.info("Scheduler started: %d jobs", len(settings.schedule_times))


def shutdown_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")


async def _run_all_categories(settings: Settings, run_pipeline) -> None:
    """Run the pipeline for each configured category."""
    for cat in settings.categories:
        try:
            result = await run_pipeline(cat.slug)
            logger.info(
                "Pipeline complete for '%s': fetched=%d, new=%d, duplicates=%d, status=%s",
                cat.slug,
                result.get("items_fetched", 0),
                result.get("items_new", 0),
                result.get("items_duplicate", 0),
                result.get("status", "unknown"),
            )
        except Exception as e:
            logger.exception("Pipeline failed for category '%s': %s", cat.slug, e)
