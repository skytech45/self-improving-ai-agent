"""
orchestration/task_planner.py

Task Decomposition + Planning Engine.
Breaks complex tasks into ordered, atomic sub-tasks
each mapped to a specific tool or agent.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


TOOL_KEYWORDS: Dict[str, List[str]] = {
    "coding_agent": [
        "write", "code", "implement", "function", "class",
        "debug", "fix", "refactor", "optimize", "script", "module",
    ],
    "web_agent": [
        "website", "html", "css", "frontend", "backend", "api",
        "fastapi", "flask", "endpoint", "scaffold", "landing",
    ],
    "security_agent": [
        "scan", "port", "vulnerability", "header", "hash",
        "audit", "pentest", "subdomain", "password", "injection",
    ],
    "multi_agent_debate": [
        "design", "architecture", "review", "evaluate",
        "best approach", "compare", "should i", "which is",
    ],
    "file_tool": [
        "read file", "write file", "create file", "save", "open",
    ],
    "search_tool": [
        "search", "find", "lookup", "research",
    ],
}


@dataclass
class SubTask:
    """Atomic executable unit of a task plan."""
    sub_id:   str
    tool:     str
    args:     Dict[str, Any]
    depends:  List[str]  = field(default_factory=list)
    priority: int        = 0


@dataclass
class TaskPlan:
    """Full decomposed plan for a task."""
    plan_id:   str
    raw_input: str
    sub_tasks: List[SubTask]
    metadata:  Dict[str, Any] = field(default_factory=dict)


class TaskPlanner:
    """
    Rule-based task planner with keyword routing.

    Decomposes a natural language task into an ordered list
    of SubTask objects. Designed to be upgraded with LLM-based
    chain-of-thought planning without changing the interface.
    """

    def decompose(self, task: str) -> TaskPlan:
        """
        Decompose a task into a TaskPlan.

        Args:
            task: Sanitized natural language task

        Returns:
            TaskPlan with ordered SubTask list
        """
        plan_id   = str(uuid.uuid4())[:8]
        sub_tasks = self._route(task)
        return TaskPlan(
            plan_id=plan_id,
            raw_input=task,
            sub_tasks=sub_tasks,
            metadata={"routing": "keyword", "sub_count": len(sub_tasks)},
        )

    def _route(self, task: str) -> List[SubTask]:
        """Map task to tool(s) via keyword matching."""
        task_lower  = task.lower()
        sub_tasks   = []
        sub_id_base = str(uuid.uuid4())[:4]

        scored: Dict[str, int] = {}
        for tool, keywords in TOOL_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            if score:
                scored[tool] = score

        if not scored:
            # Default: coding agent
            scored["coding_agent"] = 1

        # Take top-2 scoring tools
        top_tools = sorted(scored, key=scored.get, reverse=True)[:2]

        for i, tool in enumerate(top_tools):
            sub_tasks.append(SubTask(
                sub_id   = f"{sub_id_base}-{i}",
                tool     = tool,
                args     = {"task": task},
                priority = scored[tool],
            ))

        return sub_tasks
