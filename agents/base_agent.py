"""
agents/base_agent.py

Abstract base class for all agents in the multi-agent system.
Every agent must implement: execute(), can_handle(), critique().
Provides: structured output, scoring, logging, timing.
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils.logger import get_logger


@dataclass
class AgentResult:
    """Structured, typed result from any agent execution."""
    agent_name:  str
    task_id:     str     = field(default_factory=lambda: str(uuid.uuid4())[:8])
    output:      str     = ""
    confidence:  float   = 0.0      # 0.0 – 1.0
    issues:      List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    passed:      bool    = True
    elapsed_s:   float   = 0.0
    metadata:    Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent":       self.agent_name,
            "task_id":     self.task_id,
            "confidence":  self.confidence,
            "issues":      self.issues,
            "suggestions": self.suggestions,
            "passed":      self.passed,
            "elapsed_s":   self.elapsed_s,
            "output_len":  len(self.output),
        }

    def score(self) -> float:
        """Composite score: confidence penalised by issues."""
        penalty = min(len(self.issues) * 0.1, 0.5)
        return max(0.0, self.confidence - penalty)


class BaseAgent(ABC):
    """
    Abstract base for all AI agents.

    Subclasses must implement:
    - execute(task) → AgentResult
    - can_handle(task) → bool
    - critique(result) → AgentResult  (review another agent's output)
    """

    def __init__(self, name: str, memory=None, config: Dict[str, Any] = None):
        self.name    = name
        self.memory  = memory
        self.config  = config or {}
        self.logger  = get_logger(name)
        self._runs   = 0
        self._total_t = 0.0

    @abstractmethod
    def execute(self, task: str) -> AgentResult:
        """Execute a task and return a structured AgentResult."""

    @abstractmethod
    def can_handle(self, task: str) -> bool:
        """Return True if this agent is capable of handling the task."""

    @abstractmethod
    def critique(self, result: AgentResult) -> AgentResult:
        """
        Critically evaluate another agent's result.
        Returns an AgentResult describing identified issues/suggestions.
        """

    def timed_execute(self, task: str) -> AgentResult:
        """Execute with elapsed time measurement."""
        start  = time.time()
        result = self.execute(task)
        result.elapsed_s = round(time.time() - start, 4)
        self._runs       += 1
        self._total_t    += result.elapsed_s
        return result

    def get_stats(self) -> Dict[str, Any]:
        avg = self._total_t / self._runs if self._runs else 0.0
        return {
            "agent":      self.name,
            "runs":       self._runs,
            "total_s":    round(self._total_t, 3),
            "avg_s":      round(avg, 3),
        }

    def _store_context(self, task: str, result: AgentResult) -> None:
        if self.memory:
            self.memory.store_short_term(f"{self.name}_last", result.to_dict())
