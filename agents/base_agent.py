"""
agents/base_agent.py
Abstract base class for all skill agents.
Defines the standard interface all agents must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
import time


class BaseAgent(ABC):
    """
    Abstract base for all skill agents.
    Provides shared utilities: logging, timing, memory access,
    and standardized execute() interface.
    """

    def __init__(self, memory=None, config: Dict[str, Any] = None):
        self.memory = memory
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._run_count = 0
        self._total_time = 0.0

    @abstractmethod
    def execute(self, task: str) -> str:
        """
        Execute a task and return the result.

        Args:
            task: Natural language task description

        Returns:
            Result string
        """
        pass

    @abstractmethod
    def can_handle(self, task: str) -> bool:
        """
        Return True if this agent can handle the given task.

        Args:
            task: Natural language task description
        """
        pass

    def timed_execute(self, task: str) -> tuple:
        """
        Execute a task and measure elapsed time.

        Returns:
            (result, elapsed_seconds)
        """
        start = time.time()
        result = self.execute(task)
        elapsed = round(time.time() - start, 3)
        self._run_count += 1
        self._total_time += elapsed
        self.logger.debug(f"Task completed in {elapsed}s")
        return result, elapsed

    def get_stats(self) -> Dict[str, Any]:
        """Return runtime statistics for this agent."""
        avg = self._total_time / self._run_count if self._run_count else 0
        return {
            "agent": self.__class__.__name__,
            "run_count": self._run_count,
            "total_time": round(self._total_time, 3),
            "avg_time": round(avg, 3),
        }

    def _log_context(self, task: str, result: str) -> None:
        """Save task/result pair to memory for future reference."""
        if self.memory:
            self.memory.store_short_term(f"{self.__class__.__name__}_last", {
                "task": task, "result": result
            })
