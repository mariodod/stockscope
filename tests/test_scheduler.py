"""Scheduled refresh jobs are registered from settings."""

from app.worker.scheduler import build_scheduler


def test_scheduler_registers_all_refresh_jobs() -> None:
    scheduler = build_scheduler()

    jobs = {job.id: job for job in scheduler.get_jobs()}
    assert set(jobs) == {"universe", "quotes", "fundamentals"}
    for job in jobs.values():
        assert job.func.__name__ == "run_job"
