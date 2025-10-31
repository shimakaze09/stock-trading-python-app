"""Scheduling logic for pipeline execution."""

import time
import schedule
from typing import Callable, Optional
from datetime import datetime, timedelta

from config import get_settings


class PipelineScheduler:
    """Schedules pipeline execution at regular intervals."""
    
    def __init__(self, pipeline_func: Callable):
        """Initialize pipeline scheduler.
        
        Args:
            pipeline_func: Function to call for pipeline execution
        """
        self.pipeline_func = pipeline_func
        self.settings = get_settings()
        self.running = False
    
    def schedule_interval(self, interval_minutes: Optional[int] = None):
        """Schedule pipeline to run at regular intervals.
        
        Args:
            interval_minutes: Interval in minutes (default: from settings)
        """
        interval = interval_minutes or self.settings.UPDATE_INTERVAL_MINUTES
        
        # Schedule job
        schedule.every(interval).minutes.do(self._run_pipeline)
        
        print(f"Pipeline scheduled to run every {interval} minutes.")
    
    def schedule_time(self, time_str: str):
        """Schedule pipeline to run at specific time each day.
        
        Args:
            time_str: Time in HH:MM format (e.g., "09:30")
        """
        schedule.every().day.at(time_str).do(self._run_pipeline)
        
        print(f"Pipeline scheduled to run daily at {time_str}.")
    
    def schedule_multiple(self, times: list):
        """Schedule pipeline to run at multiple times each day.
        
        Args:
            times: List of time strings in HH:MM format
        """
        for time_str in times:
            schedule.every().day.at(time_str).do(self._run_pipeline)
        
        print(f"Pipeline scheduled to run at {len(times)} times daily: {', '.join(times)}")
    
    def _run_pipeline(self):
        """Run the pipeline function."""
        try:
            print(f"\n[{datetime.now()}] Running scheduled pipeline...")
            self.pipeline_func()
            print(f"[{datetime.now()}] Pipeline execution completed.")
        except Exception as e:
            print(f"[{datetime.now()}] Error running pipeline: {str(e)}")
    
    def run_continuously(self):
        """Run scheduler continuously (blocking)."""
        self.running = True
        
        print("Scheduler started. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\nScheduler stopped.")
            self.running = False
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        schedule.clear()
        print("Scheduler stopped.")

