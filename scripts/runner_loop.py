"""Long-running runner that executes the pipeline in a loop within GH Actions limits."""

import os
import time
import math
from datetime import datetime, timedelta

from database.connection import get_db_context
from pipeline.orchestrator import PipelineOrchestrator
from config import get_settings


def run_once(limit: int | None) -> bool:
    """Run the pipeline once. Returns True on success."""
    try:
        with get_db_context() as db:
            orchestrator = PipelineOrchestrator(db)
            orchestrator.run_full_pipeline(
                symbols=None,
                limit=limit,
                fetch_data=True,
                calculate_indicators=True,
                analyze_fundamentals=True,
                train_models=True,
                generate_predictions=True,
                generate_reports=True,
                export_json=True,
                display_cli=False,
            )
        return True
    except Exception as e:
        print(f"[runner_loop] Error in run_once: {e}")
        return False


def main():
    settings = get_settings()
    max_hours = float(os.getenv("MAX_HOURS", "5.5"))  # stay within GH Actions 6h cap
    sleep_minutes = int(os.getenv("SLEEP_MINUTES", str(settings.UPDATE_INTERVAL_MINUTES)))
    max_symbols_per_run = int(os.getenv("MAX_SYMBOLS_PER_RUN", str(settings.MAX_SYMBOLS_PER_RUN)))

    started = datetime.utcnow()
    cutoff = started + timedelta(hours=max_hours)
    iter_num = 0

    print(f"[runner_loop] Starting loop at {started.isoformat()}, cutoff at {cutoff.isoformat()}")
    print(f"[runner_loop] Each iteration processes up to {max_symbols_per_run} symbols; sleeping {sleep_minutes} minutes between runs")

    while datetime.utcnow() < cutoff:
        iter_num += 1
        print(f"\n[runner_loop] Iteration {iter_num} - {datetime.utcnow().isoformat()}")
        ok = run_once(limit=max_symbols_per_run)
        # Sleep regardless to respect API limits
        next_sleep = max(1, sleep_minutes) * 60
        # If error, backoff a bit more
        if not ok:
            next_sleep = int(next_sleep * 1.5)
            print(f"[runner_loop] Error occurred, backing off to {next_sleep} seconds")
        else:
            print(f"[runner_loop] Run complete, sleeping {next_sleep} seconds")
        # Prevent sleeping past cutoff too much
        remaining = (cutoff - datetime.utcnow()).total_seconds()
        if remaining <= 0:
            break
        time.sleep(min(next_sleep, int(remaining)))

    print(f"[runner_loop] Exiting at {datetime.utcnow().isoformat()} after {iter_num} iterations")


if __name__ == "__main__":
    main()


