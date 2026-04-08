"""
Fortnightly scheduler using the `schedule` library.

Run this as a long-running process:
  python scheduler.py

Or use the GitHub Actions workflow (.github/workflows/newsletter.yml) for
serverless fortnightly execution (recommended for production).
"""

import logging
import time
from datetime import datetime

import schedule

logger = logging.getLogger(__name__)


def _run_newsletter_job():
    """Called by the scheduler — imports main to avoid circular deps."""
    from main import run_newsletter_pipeline
    logger.info("Scheduler triggered newsletter job at %s", datetime.now().isoformat())
    run_newsletter_pipeline()


def start_fortnightly_scheduler(day_of_week: str = "monday", time_of_day: str = "08:00"):
    """
    Runs the newsletter job every 14 days (every other Monday at 08:00 by default).

    day_of_week: "monday" | "tuesday" | ... | "sunday"
    time_of_day: "HH:MM" in 24h format
    """
    logger.info(
        "Starting fortnightly scheduler — every other %s at %s",
        day_of_week.capitalize(),
        time_of_day,
    )

    _week_counter = {"n": 0}

    def _biweekly_gate():
        _week_counter["n"] += 1
        if _week_counter["n"] % 2 == 0:
            _run_newsletter_job()
        else:
            logger.info("Skipping this week (not a newsletter week)")

    # Schedule the gate to run every week on the specified day
    getattr(schedule.every(), day_of_week).at(time_of_day).do(_biweekly_gate)

    logger.info("Scheduler running. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    start_fortnightly_scheduler()
