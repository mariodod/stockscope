"""Scheduled refresh jobs are registered from settings."""

from typing import Any

from app.worker.scheduler import build_scheduler


def test_scheduler_registers_all_refresh_jobs() -> None:
    scheduler = build_scheduler()

    jobs = {job.id: job for job in scheduler.get_jobs()}
    assert set(jobs) == {
        "universe",
        "quotes",
        "fundamentals",
        "history",
        "dividends",
        "filings",
        "prune",
    }
    for job in jobs.values():
        assert job.func.__name__ == "run_job"


def test_worker_process_starts_and_stops_scheduler(monkeypatch: Any) -> None:
    from app.worker.__main__ import main

    stopped: list[bool] = []

    class FakeScheduler:
        def shutdown(self, wait: bool) -> None:
            stopped.append(wait)

    monkeypatch.setattr("app.worker.__main__.start_scheduler", lambda: FakeScheduler())

    def interrupt(seconds: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("app.worker.__main__.time.sleep", interrupt)

    main()

    assert stopped == [False]
