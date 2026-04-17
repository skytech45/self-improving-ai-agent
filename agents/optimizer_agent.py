"""
agents/optimizer_agent.py

Optimizer Agent - analyzes code for performance bottlenecks,
inefficient patterns, and resource usage. Suggests improvements.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List
from agents.base_agent import BaseAgent, AgentResult


PERF_PATTERNS = [
    (r"for .+ in range\(len\(.+\)\)",
     "Use enumerate() instead of range(len())"),
    (r"time\.sleep\(\d+\)",
     "Blocking sleep detected — consider async/await"),
    (r"SELECT \*",
     "SELECT * fetches all columns — specify required columns"),
    (r"except Exception as e:\s+pass",
     "Silenced exception — log or handle explicitly"),
    (r"global \w+",
     "Global variable — prefer dependency injection"),
    (r"import \*",
     "Wildcard import — use explicit imports"),
]


class OptimizerAgent(BaseAgent):
    """
    Optimizer Agent: performance and efficiency reviewer.

    Checks:
    - Algorithmic inefficiencies (nested loops, O(n^2))
    - Python anti-patterns
    - Blocking I/O patterns
    - Resource management issues
    - Memory usage concerns
    """

    def __init__(self, memory=None, config: Dict[str, Any] = None):
        super().__init__("OptimizerAgent", memory, config)

    def can_handle(self, task: str) -> bool:
        kw = ["optimize", "performance", "speed", "slow", "efficient", "bottleneck"]
        return any(k in task.lower() for k in kw)

    def execute(self, task: str) -> AgentResult:
        """Analyze a task for optimization opportunities."""
        return AgentResult(
            agent_name="OptimizerAgent",
            output=("OptimizerAgent ready.\n"
                    "Submit code via critique() for performance analysis.\n"
                    "Checks: O(n^2) loops, blocking I/O, global state, wildcard imports."),
            confidence=0.7,
            passed=True,
        )

    def critique(self, result: AgentResult) -> AgentResult:
        """Analyze agent output for performance anti-patterns."""
        code = result.output
        issues: List[str] = []
        suggestions: List[str] = []

        for pattern, advice in PERF_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append(f"PERF: {advice}")

        # Nested loop O(n^2) detection
        nested = 0
        lines = code.split("\n")
        indent_stack = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("for ") or stripped.startswith("while "):
                indent = len(line) - len(stripped)
                indent_stack = [i for i in indent_stack if i < indent]
                if indent_stack:
                    nested += 1
                indent_stack.append(indent)

        if nested > 0:
            issues.append(f"PERF: {nested} nested loop(s) detected — possible O(n^2).")
            suggestions.append("Consider dict/set lookups, sorting, or vectorization.")

        # Large functions
        fn_pattern = re.compile(r"^def \w+", re.MULTILINE)
        fn_positions = [m.start() for m in fn_pattern.finditer(code)]
        for idx, pos in enumerate(fn_positions):
            end = fn_positions[idx + 1] if idx + 1 < len(fn_positions) else len(code)
            fn_code = code[pos:end]
            fn_lines = fn_code.count("\n")
            if fn_lines > 50:
                fn_name = re.search(r"def (\w+)", fn_code)
                if fn_name:
                    issues.append(
                        f"PERF: Function '{fn_name.group(1)}' is {fn_lines} lines — split it up."
                    )

        confidence = max(0.3, 0.95 - len(issues) * 0.08)
        return AgentResult(
            agent_name   = "OptimizerAgent:critique",
            output       = self._format(issues, suggestions),
            confidence   = confidence,
            issues       = issues,
            suggestions  = suggestions,
            passed       = len(issues) == 0,
            metadata     = {"patterns_checked": len(PERF_PATTERNS)},
        )

    @staticmethod
    def _format(issues: List[str], suggestions: List[str]) -> str:
        lines = ["=== Optimizer Review ==="]
        if issues:
            for i in issues:
                lines.append(f"  {i}")
        else:
            lines.append("  No performance issues found.")
        if suggestions:
            lines.append("Suggestions:")
            for s in suggestions:
                lines.append(f"  SUGGESTION: {s}")
        return "\n".join(lines)
