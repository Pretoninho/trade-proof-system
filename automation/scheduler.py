# automation/scheduler.py
# Autonomous scheduler — runs the full analysis pipeline on a fixed interval
# without any manual intervention.
#
# Usage:
#   from automation.scheduler import start_scheduler
#   start_scheduler(interval_hours=24)
#
# Or from the command line via main.py:
#   python main.py --schedule
#   python main.py --schedule --interval 12

from __future__ import annotations

import datetime
import time

from automation.pipeline import run_pipeline


def start_scheduler(interval_hours: float = 24) -> None:
    """Run the pipeline repeatedly, pausing *interval_hours* between cycles.

    The scheduler loops indefinitely.  Each iteration:

    1. Prints a timestamped start banner.
    2. Calls :func:`automation.pipeline.run_pipeline`.
    3. Prints the generated report.
    4. Sleeps for *interval_hours* hours.

    Exceptions raised by the pipeline are caught and logged so that a
    transient network error does not kill the scheduler process.

    Args:
        interval_hours: Hours to wait between pipeline runs (default: 24).
    """
    interval_seconds = interval_hours * 3600

    while True:
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        print(f"\n[{now}] Running pipeline…")

        try:
            result = run_pipeline()
            print(result["report"])
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] Pipeline failed: {exc}")

        next_run = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            hours=interval_hours
        )
        print(f"\nNext run at {next_run.strftime('%Y-%m-%d %H:%M UTC')} "
              f"(in {interval_hours:.0f}h)…")

        time.sleep(interval_seconds)
