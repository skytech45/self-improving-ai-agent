"""
security/scanner.py

Dedicated security scanning module.
Performs static analysis on code, config files, and environment.
Separate from SecurityAgent to allow standalone use in CI/CD.
"""
from __future__ import annotations

import re
import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils.logger import get_logger


@dataclass
class SecurityFinding:
    """A single security issue found during scanning."""
    severity:    str          # CRITICAL | HIGH | MEDIUM | LOW | INFO
    category:    str          # injection | credential | crypto | config | ...
    description: str
    file_path:   str = ""
    line_number: int = 0
    evidence:    str = ""

    def to_dict(self) -> Dict:
        return {
            "severity":    self.severity,
            "category":    self.category,
            "description": self.description,
            "file":        self.file_path,
            "line":        self.line_number,
        }


@dataclass
class ScanReport:
    """Complete security scan report."""
    target:       str
    total_files:  int
    findings:     List[SecurityFinding] = field(default_factory=list)
    passed:       bool = True

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "HIGH")

    def summary(self) -> Dict:
        return {
            "target":    self.target,
            "files":     self.total_files,
            "passed":    self.passed,
            "critical":  self.critical_count,
            "high":      self.high_count,
            "total":     len(self.findings),
        }


# ── Detection Rules ────────────────────────────────────────────────────────────
STATIC_RULES: List[Tuple[str, str, str, str]] = [
    # (pattern, severity, category, description)
    (r"eval\s*\(",                     "CRITICAL", "injection",   "eval() — RCE risk"),
    (r"exec\s*\(",                     "CRITICAL", "injection",   "exec() — RCE risk"),
    (r"pickle\.loads?\s*\(",           "CRITICAL", "deser",       "pickle.load() — deserialization RCE"),
    (r"yaml\.load\s*\([^,)]+\)",       "HIGH",     "deser",       "yaml.load without Loader"),
    (r"subprocess\.(call|run)\s*\(",   "HIGH",     "injection",   "subprocess — verify no shell=True"),
    (r"os\.system\s*\(",               "HIGH",     "injection",   "os.system() — direct shell exec"),
    (r"__import__\s*\(",               "HIGH",     "injection",   "Dynamic __import__()"),
    (r"UNION\s+SELECT",                "HIGH",     "sqli",        "SQL UNION injection pattern"),
    (r";\s*DROP\s+TABLE",              "CRITICAL", "sqli",        "SQL DROP TABLE injection"),
    (r"'.*OR.*'.*=.*'",                "HIGH",     "sqli",        "Classic SQL OR injection pattern"),
    (r"(password|passwd|secret|token|apikey|api_key)\s*=\s*['\"][^'\"]{4,}['\"]",
                                       "CRITICAL", "credential",  "Hardcoded credential"),
    (r"-----BEGIN (RSA|EC|DSA) PRIVATE KEY-----",
                                       "CRITICAL", "credential",  "Private key in source code"),
    (r"md5\s*\(",                      "LOW",      "crypto",      "MD5 is weak — use SHA-256+"),
    (r"hashlib\.md5\s*\(",             "LOW",      "crypto",      "MD5 hash usage"),
    (r"DES\b|RC4\b|RC2\b",             "HIGH",     "crypto",      "Weak cipher algorithm"),
    (r"ssl\.CERT_NONE",                "HIGH",     "tls",         "SSL certificate verification disabled"),
    (r"verify\s*=\s*False",            "MEDIUM",   "tls",         "TLS verification disabled"),
    (r"<script[^>]*>.*?</script>",     "HIGH",     "xss",         "Inline script — XSS risk"),
    (r"innerHTML\s*=",                 "MEDIUM",   "xss",         "innerHTML assignment — XSS risk"),
    (r"document\.write\s*\(",          "MEDIUM",   "xss",         "document.write() — XSS risk"),
    (r"random\.random\s*\(",           "LOW",      "crypto",      "Non-cryptographic RNG — use secrets module"),
]


class SecurityScanner:
    """
    Static security scanner for Python code and config files.

    Implements SAST (Static Application Security Testing) rules
    based on OWASP Top 10 and Python security best practices.
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = get_logger("SecurityScanner")

    def scan_code(self, code: str, file_path: str = "inline") -> ScanReport:
        """
        Scan a code string for security issues.

        Args:
            code:      Source code string
            file_path: Label for the report

        Returns:
            ScanReport with all findings
        """
        findings: List[SecurityFinding] = []
        lines     = code.split("\n")

        for i, line in enumerate(lines, 1):
            for pattern, severity, category, desc in STATIC_RULES:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(SecurityFinding(
                        severity    = severity,
                        category    = category,
                        description = desc,
                        file_path   = file_path,
                        line_number = i,
                        evidence    = line.strip()[:100],
                    ))

        # AST-level checks
        ast_findings = self._ast_scan(code, file_path)
        findings.extend(ast_findings)

        passed = not any(f.severity in ("CRITICAL", "HIGH") for f in findings)
        report = ScanReport(
            target      = file_path,
            total_files = 1,
            findings    = findings,
            passed      = passed,
        )
        self.logger.info(
            f"Scan: {file_path} | {len(findings)} finding(s) | passed={passed}"
        )
        return report

    def scan_directory(self, path: str) -> ScanReport:
        """
        Scan all Python files in a directory.

        Args:
            path: Directory path

        Returns:
            Aggregate ScanReport
        """
        root     = Path(path)
        py_files = list(root.rglob("*.py"))
        all_findings: List[SecurityFinding] = []

        for pf in py_files:
            try:
                code    = pf.read_text(encoding="utf-8", errors="ignore")
                report  = self.scan_code(code, str(pf))
                all_findings.extend(report.findings)
            except Exception as exc:
                self.logger.error(f"Scan error {pf}: {exc}")

        passed = not any(f.severity in ("CRITICAL", "HIGH") for f in all_findings)
        return ScanReport(
            target      = path,
            total_files = len(py_files),
            findings    = all_findings,
            passed      = passed,
        )

    def _ast_scan(self, code: str, file_path: str) -> List[SecurityFinding]:
        """AST-based checks for patterns that regex can't catch."""
        findings = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            # assert statements in production code
            if isinstance(node, ast.Assert):
                findings.append(SecurityFinding(
                    severity    = "LOW",
                    category    = "reliability",
                    description = "assert statement — disabled with python -O flag",
                    file_path   = file_path,
                    line_number = node.lineno,
                ))
            # Dangerous default mutable arguments
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        findings.append(SecurityFinding(
                            severity    = "LOW",
                            category    = "reliability",
                            description = f"Mutable default argument in {node.name}()",
                            file_path   = file_path,
                            line_number = node.lineno,
                        ))
        return findings

    def format_report(self, report: ScanReport) -> str:
        """Format scan report as readable string."""
        status = "PASSED" if report.passed else "FAILED"
        lines  = [
            "=" * 60,
            f"  SECURITY SCAN REPORT — {status}",
            "=" * 60,
            f"  Target : {report.target}",
            f"  Files  : {report.total_files}",
            f"  Findings: {len(report.findings)} "
            f"(CRITICAL={report.critical_count}, HIGH={report.high_count})",
            "-" * 60,
        ]
        for f in sorted(report.findings, key=lambda x: x.severity):
            lines.append(
                f"  [{f.severity:<8}] {f.category:<12} "
                f"L{f.line_number}: {f.description}"
            )
        if not report.findings:
            lines.append("  No security issues found.")
        lines.append("=" * 60)
        return "\n".join(lines)
