"""APScheduler setup for periodic ingestion."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.ingestion.runner import run_job


def build_scheduler() -> BackgroundScheduler:
    """Build the scheduler with all refresh jobs, without starting it."""
    scheduler = BackgroundScheduler()
    jobs = (
        ("universe", settings.universe_refresh_cron),
        ("quotes", settings.quote_refresh_cron),
        ("fundamentals", settings.fundamentals_refresh_cron),
    )
    for name, cron in jobs:
        scheduler.add_job(
            run_job,
            CronTrigger.from_crontab(cron),
            args=[name],
            id=name,
            replace_existing=True,
        )
    return scheduler


def start_scheduler() -> BackgroundScheduler:
    scheduler = build_scheduler()
    scheduler.start()
    return scheduler
