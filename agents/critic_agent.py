"""
agents/critic_agent.py

Critic Agent - adversarially reviews Builder outputs.
Identifies logical flaws, missing edge cases, poor patterns.
Acts as the internal quality gatekeeper.
"""
from __future__ import annotations
import ast
import re
from typing import Any, Dict, List
from agents.base_agent import BaseAgent, AgentResult


class CriticAgent(BaseAgent):
    """
    Critic Agent: adversarial reviewer for all agent outputs.

    Checks:
    - Syntax correctness
    - Missing error handling
    - Missing type annotations
    - Missing docstrings
    - Security anti-patterns
    - Logic completeness
    """

    def __init__(self, memory=None, config: Dict[str, Any] = None):
        super().__init__("CriticAgent", memory, config)

    def can_handle(self, task: str) -> bool:
        return True  # Critic reviews everything

    def execute(self, task: str) -> AgentResult:
        """Perform a standalone critique of a task description."""
        issues = []
        if len(task.strip()) < 10:
            issues.append("Task description too vague — ambiguous output expected.")
        if not any(kw in task.lower() for kw in
                   ["function", "class", "api", "tool", "script", "system"]):
            issues.append("Task lacks clear deliverable specification.")
        conf = max(0.4, 0.9 - len(issues) * 0.15)
        return AgentResult(
            agent_name="CriticAgent",
            output=f"Task critique: {len(issues)} concern(s) found.",
            confidence=conf,
            issues=issues,
            passed=len(issues) == 0,
        )

    def critique(self, result: AgentResult) -> AgentResult:
        """
        Deeply critique an AgentResult from any agent.
        Returns structured critique with issues and suggestions.
        """
        issues: List[str] = []
        suggestions: List[str] = []
        code = result.output

        # Syntax check
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(f"SyntaxError: {e}")

        # Missing error handling
        if "def " in code and "try:" not in code and "raise" not in code:
            issues.append("No exception handling — functions may fail silently.")
            suggestions.append("Add try/except blocks to all public functions.")

        # Missing type hints
        fn_defs = re.findall(r"def (\w+)\(", code)
        untyped = [
            f for f in fn_defs
            if f not in ["__init__", "setUp", "tearDown"]
            and "->" not in code[code.find(f"def {f}"):code.find(f"def {f}") + 80]
        ]
        if untyped:
            issues.append(f"Missing return type hints on: {untyped[:3]}")
            suggestions.append("Add return type annotations to all functions.")

        # Missing docstrings — check without using triple-quote in the check itself
        dq = chr(34) * 3
        sq = chr(39) * 3
        if "def " in code and dq not in code and sq not in code:
            issues.append("No docstrings found.")
            suggestions.append("Add Google-style docstrings to all public methods.")

        # Bare except
        if "except:" in code:
            issues.append("Bare except clause — catches everything including SystemExit.")
            suggestions.append("Replace bare except with specific exception types.")

        # Hardcoded credentials
        cred_pattern = r"(password|secret|token|apikey)\s*=\s*['\"][^'\"]{4,}['\"]"
        if re.search(cred_pattern, code, re.IGNORECASE):
            issues.append("Possible hardcoded credential detected.")
            suggestions.append("Use os.environ or config file for sensitive values.")

        confidence = max(0.1, 1.0 - len(issues) * 0.12)
        return AgentResult(
            agent_name   = "CriticAgent:critique",
            output       = self._format(issues, suggestions),
            confidence   = confidence,
            issues       = issues,
            suggestions  = suggestions,
            passed       = not any("Syntax" in i for i in issues),
            metadata     = {"reviewed_agent": result.agent_name},
        )

    @staticmethod
    def _format(issues: List[str], suggestions: List[str]) -> str:
        lines = ["=== Critic Review ==="]
        if issues:
            lines.append(f"Issues ({len(issues)}):")
            for i in issues:
                lines.append(f"  ISSUE: {i}")
        else:
            lines.append("  No critical issues found.")
        if suggestions:
            lines.append(f"Suggestions ({len(suggestions)}):")
            for s in suggestions:
                lines.append(f"  SUGGESTION: {s}")
        return "\n".join(lines)
