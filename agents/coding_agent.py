"""
agents/coding_agent.py
Coding skill agent — writes, debugs, and refactors Python code.
Uses LLM as a reasoning engine with rule-based validation.
"""

import re
import ast
import subprocess
import tempfile
import os
from typing import Any, Dict, Optional

from agents.base_agent import BaseAgent


class CodingAgent(BaseAgent):
    """
    Coding Agent for software development tasks.

    Capabilities:
    - Write Python functions, classes, and scripts
    - Debug and fix syntax/logic errors
    - Refactor code for clarity and performance
    - Add docstrings and type hints
    - Generate unit tests
    """

    SUPPORTED_KEYWORDS = [
        "write", "code", "script", "function", "class",
        "debug", "fix", "refactor", "optimize", "implement",
        "generate", "create", "build", "test", "module",
    ]

    def __init__(self, memory=None, config: Dict[str, Any] = None):
        super().__init__(memory, config)
        self.language = config.get("language", "python") if config else "python"
        self.logger.info(f"CodingAgent initialized (language: {self.language})")

    def can_handle(self, task: str) -> bool:
        """Check if this agent can handle the given task."""
        task_lower = task.lower()
        return any(kw in task_lower for kw in self.SUPPORTED_KEYWORDS)

    def execute(self, task: str) -> str:
        """
        Execute a coding task.

        Workflow:
        1. Parse task intent
        2. Generate code scaffold
        3. Validate syntax
        4. Optionally run in sandbox
        5. Return result

        Args:
            task: Coding task description

        Returns:
            Generated or processed code as string
        """
        self.logger.info(f"CodingAgent executing: {task[:60]}...")

        intent = self._detect_intent(task)

        if intent == "debug":
            return self._debug_task(task)
        elif intent == "test":
            return self._generate_tests(task)
        elif intent == "refactor":
            return self._refactor_task(task)
        else:
            return self._write_code(task)

    def _detect_intent(self, task: str) -> str:
        """Detect the coding intent from task description."""
        task_lower = task.lower()
        if any(w in task_lower for w in ["debug", "fix", "error", "bug"]):
            return "debug"
        if any(w in task_lower for w in ["test", "unittest", "pytest"]):
            return "test"
        if any(w in task_lower for w in ["refactor", "optimize", "clean"]):
            return "refactor"
        return "write"

    def _write_code(self, task: str) -> str:
        """Generate a code scaffold for the requested task."""
        # Extract function/class name from task
        name = self._extract_name(task)
        template = self._build_template(name, task)
        valid, errors = self.validate_syntax(template)
        if not valid:
            self.logger.warning(f"Generated code has syntax issues: {errors}")
        self._log_context(task, template)
        return template

    def _debug_task(self, task: str) -> str:
        """Analyze a debugging request and suggest fixes."""
        return (
            f"# Debug Analysis\n"
            f"# Task: {task}\n"
            f"# Suggested steps:\n"
            f"# 1. Check for syntax errors using: python -m py_compile <file>\n"
            f"# 2. Run with verbose: python -v <file>\n"
            f"# 3. Add logging.basicConfig(level=logging.DEBUG)\n"
            f"# 4. Use pdb: import pdb; pdb.set_trace()\n"
        )

    def _generate_tests(self, task: str) -> str:
        """Generate a unit test scaffold."""
        name = self._extract_name(task)
        return (
            f'''import unittest\n\n
class Test{name.capitalize()}(unittest.TestCase):\n
    def setUp(self):\n
        """Set up test fixtures."""\n
        pass\n\n
    def test_basic_functionality(self):\n
        """Test basic functionality of {name}."""\n
        # TODO: implement test\n
        self.assertTrue(True)\n\n
    def test_edge_cases(self):\n
        """Test edge cases and boundary conditions."""\n
        # TODO: implement edge case tests\n
        pass\n\n
if __name__ == "__main__":\n
    unittest.main()\n'''
        )

    def _refactor_task(self, task: str) -> str:
        """Generate a refactoring guide."""
        return (
            f"# Refactoring Guide\n"
            f"# Task: {task}\n\n"
            f"# Principles applied:\n"
            f"# 1. Single Responsibility Principle (SRP)\n"
            f"# 2. DRY — Don't Repeat Yourself\n"
            f"# 3. Type hints added to all functions\n"
            f"# 4. Docstrings added to all public methods\n"
            f"# 5. Extract long functions into smaller helpers\n"
            f"# 6. Replace magic numbers with named constants\n"
        )

    def _extract_name(self, task: str) -> str:
        """Extract a likely identifier name from task text."""
        words = re.findall(r'[a-zA-Z]+', task)
        stopwords = {"write", "create", "build", "make", "a", "an", "the",
                     "for", "that", "which", "python", "function", "class"}
        candidates = [w.lower() for w in words if w.lower() not in stopwords]
        return "_".join(candidates[:2]) if candidates else "my_function"

    def _build_template(self, name: str, task: str) -> str:
        """Build a Python function template."""
        return (
            f'''def {name}():\n
    """\n
    {task.strip()}\n\n
    Returns:\n
        TODO: describe return value\n
    """\n
    # TODO: implement logic\n
    raise NotImplementedError("{name} is not yet implemented")\n'''
        )

    @staticmethod
    def validate_syntax(code: str) -> tuple:
        """
        Validate Python code syntax using ast.parse.

        Args:
            code: Python source code string

        Returns:
            (is_valid, error_message_or_None)
        """
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, str(e)

    def run_in_sandbox(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Execute code in a sandboxed subprocess with timeout.

        Args:
            code:    Python code to execute
            timeout: Max execution time in seconds

        Returns:
            dict with keys: success, stdout, stderr, return_code
        """
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ["python3", tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:2000],
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "Execution timed out.", "return_code": -1}
        finally:
            os.unlink(tmp_path)
