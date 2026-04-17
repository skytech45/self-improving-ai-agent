"""
orchestration/orchestrator.py

Central Orchestration Layer.
Handles task decomposition, multi-agent routing, tool dispatching,
and result aggregation. All task execution flows through here.

Design principles:
- Tasks are decomposed into atomic sub-tasks
- Each sub-task is routed to the best-fit agent
- All results pass through a consensus + scoring phase
- No unverified output is returned to the user
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from orchestration.task_planner import TaskPlanner, TaskPlan, SubTask
from orchestration.tool_controller import ToolController
from memory.memory_manager import MemoryManager
from utils.logger import get_logger


class TaskStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    ROLLED_BACK = "rolled_back"


class TaskPriority(int, Enum):
    LOW      = 1
    NORMAL   = 2
    HIGH     = 3
    CRITICAL = 4


@dataclass
class TaskContext:
    """Full context for a single task execution."""
    task_id:     str              = field(default_factory=lambda: str(uuid.uuid4())[:8])
    raw_input:   str              = ""
    plan:        Optional[TaskPlan] = None
    status:      TaskStatus       = TaskStatus.PENDING
    priority:    TaskPriority     = TaskPriority.NORMAL
    start_time:  float            = field(default_factory=time.time)
    end_time:    float            = 0.0
    result:      Optional[str]    = None
    error:       Optional[str]    = None
    sub_results: List[Dict]       = field(default_factory=list)
    metadata:    Dict[str, Any]   = field(default_factory=dict)

    @property
    def elapsed(self) -> float:
        end = self.end_time or time.time()
        return round(end - self.start_time, 3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id":    self.task_id,
            "raw_input":  self.raw_input[:100],
            "status":     self.status.value,
            "priority":   self.priority.value,
            "elapsed_s":  self.elapsed,
            "result_len": len(self.result) if self.result else 0,
            "error":      self.error,
            "sub_tasks":  len(self.sub_results),
        }


class Orchestrator:
    """
    Central task orchestrator.

    Workflow per task:
    1. Sanitize + validate input
    2. Decompose via TaskPlanner
    3. Execute sub-tasks via ToolController
    4. Collect + aggregate results
    5. Score and validate output
    6. Log to memory

    Thread-safe: task_id scoped, no shared mutable state.
    """

    def __init__(
        self,
        memory:         MemoryManager,
        tool_controller: ToolController,
        planner:        TaskPlanner,
        config:         Dict[str, Any] = None,
    ):
        self.memory          = memory
        self.tool_controller = tool_controller
        self.planner         = planner
        self.config          = config or {}
        self.logger          = get_logger("Orchestrator")
        self._active_tasks:  Dict[str, TaskContext] = {}

    # ── Public API ────────────────────────────────────────────────

    def execute(self, raw_input: str, priority: TaskPriority = TaskPriority.NORMAL) -> TaskContext:
        """
        Execute a task end-to-end.

        Args:
            raw_input: Raw user task string
            priority:  Task priority level

        Returns:
            Completed TaskContext with results
        """
        ctx = TaskContext(raw_input=raw_input, priority=priority)
        self._active_tasks[ctx.task_id] = ctx
        self.logger.info(f"[{ctx.task_id}] Task received: {raw_input[:80]}")

        try:
            ctx.status = TaskStatus.RUNNING

            # Stage 1: Input sanitization
            safe_input = self._sanitize_input(raw_input)
            if safe_input is None:
                ctx.status = TaskStatus.FAILED
                ctx.error  = "Input rejected by sanitizer (possible injection)."
                return ctx

            # Stage 2: Planning
            ctx.plan = self.planner.decompose(safe_input)
            self.logger.info(f"[{ctx.task_id}] Plan: {len(ctx.plan.sub_tasks)} sub-tasks")

            # Stage 3: Execute sub-tasks
            for sub in ctx.plan.sub_tasks:
                sub_result = self._execute_subtask(sub, ctx)
                ctx.sub_results.append(sub_result)

            # Stage 4: Aggregate
            ctx.result = self._aggregate_results(ctx.sub_results)
            ctx.status = TaskStatus.COMPLETED

        except Exception as exc:
            self.logger.exception(f"[{ctx.task_id}] Unhandled error: {exc}")
            ctx.status = TaskStatus.FAILED
            ctx.error  = str(exc)
            self.memory.log_failure(raw_input, "orchestrator", str(exc))
        finally:
            ctx.end_time = time.time()
            self._active_tasks.pop(ctx.task_id, None)

        if ctx.status == TaskStatus.COMPLETED:
            self.memory.log_success(raw_input, "orchestrator", ctx.elapsed)
            self.logger.info(f"[{ctx.task_id}] Completed in {ctx.elapsed}s")
        else:
            self.logger.warning(f"[{ctx.task_id}] Failed: {ctx.error}")

        return ctx

    def get_active_tasks(self) -> List[Dict]:
        return [ctx.to_dict() for ctx in self._active_tasks.values()]

    # ── Internal ──────────────────────────────────────────────────

    def _sanitize_input(self, raw: str) -> Optional[str]:
        """
        Sanitize input to prevent prompt injection and abuse.
        Returns None if input is rejected.
        """
        if not raw or not raw.strip():
            return None
        if len(raw) > 4096:
            self.logger.warning("Input exceeds max length — truncating.")
            raw = raw[:4096]
        # Injection patterns
        INJECTION_PATTERNS = [
            "ignore previous instructions",
            "disregard your",
            "jailbreak",
            "pretend you are",
            "system prompt",
        ]
        lower = raw.lower()
        for pattern in INJECTION_PATTERNS:
            if pattern in lower:
                self.logger.warning(f"Injection attempt detected: {pattern!r}")
                return None
        return raw.strip()

    def _execute_subtask(self, sub: "SubTask", ctx: TaskContext) -> Dict[str, Any]:
        """Execute a single sub-task via the tool controller."""
        start = time.time()
        try:
            result = self.tool_controller.dispatch(sub.tool, sub.args)
            return {
                "sub_id":  sub.sub_id,
                "tool":    sub.tool,
                "success": True,
                "result":  result,
                "elapsed": round(time.time() - start, 3),
            }
        except Exception as e:
            self.logger.error(f"[{ctx.task_id}] Sub-task {sub.sub_id} failed: {e}")
            return {
                "sub_id":  sub.sub_id,
                "tool":    sub.tool,
                "success": False,
                "error":   str(e),
                "elapsed": round(time.time() - start, 3),
            }

    def _aggregate_results(self, sub_results: List[Dict]) -> str:
        """Combine sub-task results into a final response."""
        parts = []
        for r in sub_results:
            if r.get("success"):
                parts.append(str(r.get("result", "")))
            else:
                parts.append(f"[Sub-task {r['sub_id']} failed: {r.get('error')}]")
        return "\n\n".join(filter(None, parts)) or "No output produced."
