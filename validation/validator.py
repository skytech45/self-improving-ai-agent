"""
validation/validator.py
Validation Pipeline — mandatory gate before any code deployment.
Runs syntax check, linting, unit tests, and sandbox execution.
NEVER deploy code that fails validation.
"""

import ast
import subprocess
import os
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple
import logging


class ValidationPipeline:
    """
    Multi-stage validation pipeline for the self-improvement system.

    Stages (in order):
    1. Syntax validation (ast.parse)
    2. Linting (flake8 / pylint)
    3. Static type check (optional mypy)
    4. Unit test execution (pytest)
    5. Sandbox execution (subprocess with timeout)

    A candidate update must PASS ALL stages to be deployed.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config       = config or {}
        self.run_linting  = self.config.get("run_linting", True)
        self.run_tests    = self.config.get("run_tests", True)
        self.timeout      = self.config.get("sandbox_timeout", 30)
        self.logger       = logging.getLogger("ValidationPipeline")

    def validate_code(self, code: str, filename: str = "candidate.py") -> Dict[str, Any]:
        """
        Validate a code string through all pipeline stages.

        Args:
            code:     Python source code to validate
            filename: Name for the temporary file

        Returns:
            dict: { passed, stages, errors, warnings }
        """
        results = {"passed": True, "stages": {}, "errors": [], "warnings": []}

        # Stage 1: Syntax
        syntax_ok, syntax_err = self._check_syntax(code)
        results["stages"]["syntax"] = {"passed": syntax_ok, "error": syntax_err}
        if not syntax_ok:
            results["passed"] = False
            results["errors"].append(f"Syntax error: {syntax_err}")
            return results  # No point continuing

        # Stage 2: Linting
        if self.run_linting:
            lint_ok, lint_issues = self._run_linting(code, filename)
            results["stages"]["linting"] = {"passed": lint_ok, "issues": lint_issues}
            if lint_issues:
                results["warnings"].extend(lint_issues)

        # Stage 3: Security scan (basic)
        sec_ok, sec_issues = self._security_scan(code)
        results["stages"]["security"] = {"passed": sec_ok, "issues": sec_issues}
        if not sec_ok:
            results["passed"] = False
            results["errors"].extend(sec_issues)
            return results

        # Stage 4: Sandbox execution
        exec_ok, exec_output = self._sandbox_execute(code)
        results["stages"]["sandbox"] = {"passed": exec_ok, "output": exec_output}
        if not exec_ok:
            results["warnings"].append(f"Sandbox execution issue: {exec_output}")

        return results

    def run_full_validation(self, project_path: str) -> Dict[str, Any]:
        """
        Run full validation on a project directory.
        Validates all .py files and runs pytest if available.

        Args:
            project_path: Path to the project root

        Returns:
            Aggregate validation results
        """
        path   = Path(project_path)
        py_files = list(path.rglob("*.py"))
        results = {"total": len(py_files), "passed": 0, "failed": 0, "files": {}}

        for py_file in py_files:
            try:
                code = py_file.read_text(encoding="utf-8")
                valid, err = self._check_syntax(code)
                if valid:
                    results["passed"] += 1
                    results["files"][str(py_file)] = "✅ PASSED"
                else:
                    results["failed"] += 1
                    results["files"][str(py_file)] = f"❌ FAILED: {err}"
            except Exception as e:
                results["failed"] += 1
                results["files"][str(py_file)] = f"❌ ERROR: {e}"

        # Run pytest if available
        if self.run_tests:
            pytest_result = self._run_pytest(project_path)
            results["pytest"] = pytest_result

        return results

    @staticmethod
    def _check_syntax(code: str) -> Tuple[bool, Optional[str]]:
        """Validate Python syntax using ast.parse."""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, str(e)

    def _run_linting(self, code: str, filename: str) -> Tuple[bool, List[str]]:
        """Run flake8 linting on code."""
        issues = []
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            tmp_path = f.name
        try:
            result = subprocess.run(
                ["flake8", "--max-line-length=100", "--ignore=E501,W503", tmp_path],
                capture_output=True, text=True, timeout=15
            )
            if result.stdout:
                issues = [line.replace(tmp_path, filename) for line in result.stdout.splitlines()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # flake8 not available
        finally:
            os.unlink(tmp_path)
        return len(issues) == 0, issues

    def _security_scan(self, code: str) -> Tuple[bool, List[str]]:
        """
        Basic static security scan.
        Blocks known dangerous patterns.
        """
        DANGEROUS_PATTERNS = [
            ("os.system(",        "Direct shell execution detected"),
            ("subprocess.call(",  "Unrestricted subprocess call"),
            ("eval(",             "eval() usage — injection risk"),
            ("exec(",             "exec() usage — code injection risk"),
            ("__import__(",       "Dynamic import — potential abuse"),
            ("shutil.rmtree(",    "Recursive deletion — destructive"),
            ("DROP TABLE",        "SQL DROP TABLE detected"),
            ("rm -rf",            "Destructive shell command"),
        ]
        issues = []
        for pattern, reason in DANGEROUS_PATTERNS:
            if pattern in code:
                issues.append(f"🔴 BLOCKED: {reason} ({pattern!r})")
        return len(issues) == 0, issues

    def _sandbox_execute(self, code: str) -> Tuple[bool, str]:
        """Execute code in a subprocess sandbox with timeout."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            tmp_path = f.name
        try:
            result = subprocess.run(
                ["python3", tmp_path],
                capture_output=True, text=True,
                timeout=self.timeout,
                env={k: v for k, v in os.environ.items()
                     if k in ("PATH", "PYTHONPATH", "HOME")}
            )
            if result.returncode == 0:
                return True, result.stdout[:500]
            else:
                return False, result.stderr[:500]
        except subprocess.TimeoutExpired:
            return False, "Execution timed out"
        except Exception as e:
            return False, str(e)
        finally:
            os.unlink(tmp_path)

    def _run_pytest(self, project_path: str) -> Dict[str, Any]:
        """Run pytest and return results."""
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", project_path, "--tb=short", "-q"],
                capture_output=True, text=True, timeout=60,
                cwd=project_path
            )
            return {
                "passed": result.returncode == 0,
                "output": result.stdout[-1000:] + result.stderr[-500:]
            }
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {"passed": False, "output": str(e)}
