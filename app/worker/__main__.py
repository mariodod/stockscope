"""Run scheduled ingestion jobs as a long-lived process."""

import time

from app.worker.scheduler import start_scheduler


def main() -> None:
    scheduler = start_scheduler()
    print("Stockscope scheduler started (Ctrl+C to stop).", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
