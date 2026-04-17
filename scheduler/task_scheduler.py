"""
scheduler/task_scheduler.py
Background task scheduler for the self-improvement pipeline.
Runs daily improvement cycles and periodic health checks.
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List


class ScheduledTask:
    """Represents a single scheduled task."""
    def __init__(self, name: str, fn: Callable, interval_hours: float):
        self.name            = name
        self.fn              = fn
        self.interval_hours  = interval_hours
        self.last_run: float = 0.0
        self.run_count: int  = 0
        self.error_count: int = 0

    def is_due(self) -> bool:
        interval_secs = self.interval_hours * 3600
        return (time.time() - self.last_run) >= interval_secs

    def run(self) -> Any:
        self.last_run = time.time()
        self.run_count += 1
        return self.fn()


class TaskScheduler:
    """
    Background scheduler that runs tasks at configured intervals.
    Runs in a daemon thread — stops when main program exits.
    """

    def __init__(self, engine, interval_hours: float = 24.0):
        self.engine         = engine
        self.interval_hours = interval_hours
        self.logger         = logging.getLogger("TaskScheduler")
        self._running       = False
        self._thread: threading.Thread = None
        self._tasks: List[ScheduledTask] = []
        self._setup_default_tasks()

    def _setup_default_tasks(self) -> None:
        """Register default scheduled tasks."""
        self._tasks.append(ScheduledTask(
            name="self_improvement_cycle",
            fn=self.engine.run_improvement_cycle,
            interval_hours=self.interval_hours
        ))
        self._tasks.append(ScheduledTask(
            name="memory_cleanup",
            fn=self.engine.memory.clear_short_term,
            interval_hours=1.0
        ))
        self._tasks.append(ScheduledTask(
            name="validation_check",
            fn=lambda: self.engine.run_validation(),
            interval_hours=12.0
        ))

    def add_task(self, name: str, fn: Callable, interval_hours: float) -> None:
        """Add a custom scheduled task."""
        self._tasks.append(ScheduledTask(name, fn, interval_hours))
        self.logger.info(f"Task added: {name} (every {interval_hours}h)")

    def start(self) -> None:
        """Start the scheduler in a daemon thread."""
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.logger.info(f"Scheduler started — {len(self._tasks)} tasks registered")
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        self.logger.info("Scheduler stopped.")

    def _loop(self) -> None:
        """Main scheduler loop — checks and runs due tasks."""
        while self._running:
            for task in self._tasks:
                if task.is_due():
                    self.logger.info(f"Running scheduled task: {task.name}")
                    try:
                        task.run()
                        self.logger.info(f"Task completed: {task.name} "
                                         f"(run #{task.run_count})")
                    except Exception as e:
                        task.error_count += 1
                        self.logger.error(f"Task failed: {task.name} — {e}")
            time.sleep(60)  # Check every minute

    def status(self) -> List[Dict]:
        """Return status of all scheduled tasks."""
        return [
            {
                "name":        t.name,
                "interval_h":  t.interval_hours,
                "run_count":   t.run_count,
                "error_count": t.error_count,
                "next_run":    (
                    datetime.fromtimestamp(t.last_run + t.interval_hours * 3600)
                    .strftime("%Y-%m-%d %H:%M") if t.last_run else "immediately"
                )
            }
            for t in self._tasks
        ]
