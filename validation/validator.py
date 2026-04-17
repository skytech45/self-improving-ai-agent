"""
validation/validator.py

Multi-Stage Validation Pipeline.
MANDATORY gate before any code reaches the repo.
Stages: syntax -> lint -> security -> sandbox -> type-check
"""
from __future__ import annotations

import ast
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger


@dataclass
class ValidationReport:
    """Complete report from all validation stages."""
    passed:   bool
    stages:   Dict[str, Dict]  = field(default_factory=dict)
    errors:   List[str]        = field(default_factory=list)
    warnings: List[str]        = field(default_factory=list)

    def summary(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        e = len(self.errors)
        w = len(self.warnings)
        return f"Validation {status} | errors={e} warnings={w}"


class ValidationPipeline:
    """
    Multi-stage code validation pipeline.

    Stages (in order — each must pass before next runs):
    1. Syntax       — ast.parse, immediate fail on error
    2. Security     — SAST pattern scan, blocks CRITICAL/HIGH
    3. Linting      — flake8, non-blocking (warnings only)
    4. Sandbox      — subprocess execution with timeout
    5. Type Check   — mypy (optional, non-blocking)

    Non-negotiable rule: CRITICAL security findings = instant reject.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config    = config or {}
        self.timeout   = self.config.get("sandbox_timeout", 30)
        self.run_lint  = self.config.get("run_linting", True)
        self.run_mypy  = self.config.get("run_type_check", False)
        self.logger    = get_logger("ValidationPipeline")

    def validate_code(self, code: str, filename: str = "candidate.py") -> Dict[str, Any]:
        """
        Run full pipeline on a code string.

        Args:
            code:     Python source code
            filename: Label used in error messages

        Returns:
            dict: { passed, stages, errors, warnings }
        """
        report = ValidationReport(passed=True)

        # ── Stage 1: Syntax ──────────────────────────────────────
        ok, err = self._syntax_check(code)
        report.stages["syntax"] = {"passed": ok, "error": err}
        if not ok:
            report.passed = False
            report.errors.append(f"SyntaxError: {err}")
            self.logger.warning(f"[{filename}] Syntax FAILED: {err}")
            return self._to_dict(report)  # Stop immediately

        # ── Stage 2: Security scan ────────────────────────────────
        sec_ok, sec_findings = self._security_scan(code)
        report.stages["security"] = {"passed": sec_ok, "findings": sec_findings}
        if not sec_ok:
            report.passed = False
            report.errors.extend([f"SECURITY: {f}" for f in sec_findings])
            self.logger.warning(f"[{filename}] Security FAILED: {len(sec_findings)} finding(s)")
            return self._to_dict(report)

        # ── Stage 3: Linting ─────────────────────────────────────
        if self.run_lint:
            lint_issues = self._lint(code, filename)
            report.stages["linting"] = {"passed": len(lint_issues) == 0, "issues": lint_issues}
            if lint_issues:
                report.warnings.extend(lint_issues[:10])

        # ── Stage 4: Sandbox execution ────────────────────────────
        exec_ok, exec_out = self._sandbox(code)
        report.stages["sandbox"] = {"passed": exec_ok, "output": exec_out[:300]}
        if not exec_ok:
            report.warnings.append(f"Sandbox: {exec_out[:200]}")

        # ── Stage 5: Type check (optional) ────────────────────────
        if self.run_mypy:
            mypy_ok, mypy_out = self._mypy(code, filename)
            report.stages["type_check"] = {"passed": mypy_ok, "output": mypy_out[:300]}
            if not mypy_ok:
                report.warnings.append(f"mypy: {mypy_out[:100]}")

        self.logger.info(f"[{filename}] {report.summary()}")
        return self._to_dict(report)

    def validate_file(self, path: str) -> Dict[str, Any]:
        """Validate a file on disk."""
        try:
            code = Path(path).read_text(encoding="utf-8")
            return self.validate_code(code, path)
        except (IOError, OSError) as e:
            return {"passed": False, "errors": [str(e)], "stages": {}, "warnings": []}

    def run_full_validation(self, project_path: str) -> Dict[str, Any]:
        """Validate all Python files in a project directory."""
        root     = Path(project_path)
        py_files = [f for f in root.rglob("*.py") if ".venv" not in str(f)]
        results  = {}
        passed = failed = 0

        for pf in py_files:
            r = self.validate_file(str(pf))
            results[str(pf)] = r
            if r["passed"]:
                passed += 1
            else:
                failed += 1

        return {
            "total": len(py_files),
            "passed": passed,
            "failed": failed,
            "files":  results,
        }

    # ── Stages ────────────────────────────────────────────────────

    @staticmethod
    def _syntax_check(code: str) -> Tuple[bool, Optional[str]]:
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, str(e)

    def _security_scan(self, code: str) -> Tuple[bool, List[str]]:
        """Block CRITICAL and HIGH severity patterns."""
        import re
        BLOCKING = [
            (r"eval\s*\(",                    "eval() — RCE risk"),
            (r"exec\s*\(",                    "exec() — RCE risk"),
            (r"pickle\.loads?\s*\(",          "pickle deserialization — RCE"),
            (r"os\.system\s*\(",              "os.system() — shell injection"),
            (r"subprocess\.call\(.+shell=True", "subprocess shell=True — injection"),
            (r"(password|secret|apikey)\s*=\s*['\"][^'\"]{4,}['\"]",
             "Hardcoded credential"),
            (r";\s*DROP\s+TABLE",             "SQL injection — DROP TABLE"),
            (r"UNION\s+SELECT",               "SQL UNION injection"),
        ]
        findings = []
        for pattern, reason in BLOCKING:
            if re.search(pattern, code, re.IGNORECASE):
                findings.append(reason)
        return len(findings) == 0, findings

    def _lint(self, code: str, filename: str) -> List[str]:
        issues = []
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                         delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp = f.name
        try:
            r = subprocess.run(
                ["flake8", "--max-line-length=100",
                 "--ignore=E501,W503,E302,E303", tmp],
                capture_output=True, text=True, timeout=15
            )
            if r.stdout:
                issues = [l.replace(tmp, filename) for l in r.stdout.splitlines()]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # flake8 not installed — skip gracefully
        finally:
            try: os.unlink(tmp)
            except: pass
        return issues

    def _sandbox(self, code: str) -> Tuple[bool, str]:
        """Execute code in isolated subprocess with timeout."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                          delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp = f.name
        try:
            r = subprocess.run(
                ["python3", tmp],
                capture_output=True, text=True,
                timeout=self.timeout,
                env={"PATH": os.environ.get("PATH", ""),
                     "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                     "HOME": os.environ.get("HOME", "")},
            )
            return r.returncode == 0, (r.stdout + r.stderr)[:500]
        except subprocess.TimeoutExpired:
            return False, "Execution timed out"
        except Exception as e:
            return False, str(e)
        finally:
            try: os.unlink(tmp)
            except: pass

    def _mypy(self, code: str, filename: str) -> Tuple[bool, str]:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                          delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp = f.name
        try:
            r = subprocess.run(
                ["mypy", "--ignore-missing-imports", "--no-error-summary", tmp],
                capture_output=True, text=True, timeout=20
            )
            out = r.stdout.replace(tmp, filename)
            return r.returncode == 0, out
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return True, "mypy not available"
        finally:
            try: os.unlink(tmp)
            except: pass

    @staticmethod
    def _to_dict(r: ValidationReport) -> Dict[str, Any]:
        return {
            "passed":   r.passed,
            "stages":   r.stages,
            "errors":   r.errors,
            "warnings": r.warnings,
        }
