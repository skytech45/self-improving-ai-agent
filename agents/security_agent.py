"""
agents/security_agent.py
Cybersecurity skill agent — performs safe, ethical security analysis.
Scope: network recon, header analysis, password auditing, hash ops.
NEVER performs destructive or unauthorized operations.
"""

import socket
import hashlib
import re
from typing import Any, Dict, List, Optional
from urllib import request as urllib_request, error as urllib_error

from agents.base_agent import BaseAgent


class SecurityAgent(BaseAgent):
    """
    Cybersecurity Agent for ethical security analysis tasks.

    Capabilities:
    - Port scanning (localhost / authorized targets only)
    - HTTP security header analysis
    - Password strength audit
    - Hash generation and verification
    - Subdomain DNS enumeration (passive)

    Strict safety rules:
    - No exploitation or payload delivery
    - No unauthorized system access
    - All operations are read-only and passive
    """

    SUPPORTED_KEYWORDS = [
        "scan", "port", "vulnerability", "header", "security",
        "hash", "password", "subdomain", "dns", "analyze", "audit",
    ]

    SAFE_TARGETS = {"localhost", "127.0.0.1", "0.0.0.0"}

    def __init__(self, memory=None, config: Dict[str, Any] = None):
        super().__init__(memory, config)
        self.sandbox_mode = config.get("sandbox_mode", True) if config else True
        self.logger.info(f"SecurityAgent initialized (sandbox={self.sandbox_mode})")

    def can_handle(self, task: str) -> bool:
        task_lower = task.lower()
        return any(kw in task_lower for kw in self.SUPPORTED_KEYWORDS)

    def execute(self, task: str) -> str:
        """
        Route security task to appropriate handler.

        Args:
            task: Security task description

        Returns:
            Analysis result as formatted string
        """
        self.logger.info(f"SecurityAgent executing: {task[:60]}...")
        task_lower = task.lower()

        if "port" in task_lower or "scan" in task_lower:
            return self._port_scan_report(task)
        elif "header" in task_lower:
            return self._header_analysis(task)
        elif "hash" in task_lower:
            return self._hash_tool(task)
        elif "password" in task_lower:
            return self._password_audit(task)
        elif "subdomain" in task_lower:
            return self._subdomain_info(task)
        else:
            return self._generic_security_advice(task)

    def _port_scan_report(self, task: str) -> str:
        """Scan common ports on localhost (sandbox-safe)."""
        target = "127.0.0.1"
        common_ports = [21, 22, 23, 25, 53, 80, 443, 3306, 5432, 6379, 8080, 8443]
        open_ports = []

        for port in common_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    if s.connect_ex((target, port)) == 0:
                        open_ports.append(port)
            except Exception:
                pass

        services = {
            21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
            53: "DNS", 80: "HTTP", 443: "HTTPS", 3306: "MySQL",
            5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt"
        }

        lines = [f"Port Scan — {target}", "-" * 40]
        if open_ports:
            for p in open_ports:
                lines.append(f"  [OPEN] {p:5d} — {services.get(p, 'Unknown')}")
        else:
            lines.append("  No open ports detected on common set.")
        lines.append(f"\nScanned: {len(common_ports)} ports | Found: {len(open_ports)} open")
        return "\n".join(lines)

    def _header_analysis(self, task: str) -> str:
        """Analyze HTTP security headers for a given URL."""
        url_match = re.search(r"https?://[^\s]+", task)
        if not url_match:
            url = "https://example.com"
        else:
            url = url_match.group(0)

        security_headers = {
            "Strict-Transport-Security": "Enforces HTTPS connections",
            "Content-Security-Policy": "Prevents XSS/injection attacks",
            "X-Frame-Options": "Prevents clickjacking",
            "X-Content-Type-Options": "Prevents MIME-type sniffing",
            "Referrer-Policy": "Controls referrer information",
            "Permissions-Policy": "Controls browser feature access",
        }

        try:
            req = urllib_request.Request(url, headers={"User-Agent": "SecurityAudit/1.0"})
            with urllib_request.urlopen(req, timeout=5) as resp:
                headers = dict(resp.headers)
        except Exception as e:
            return f"[!] Could not fetch headers from {url}: {e}"

        lines = [f"Security Header Analysis — {url}", "-" * 50]
        for header, desc in security_headers.items():
            present = header in headers or header.lower() in {k.lower(): k for k in headers}
            status  = "✅ PRESENT" if present else "❌ MISSING"
            lines.append(f"  {status} | {header}")
            if not present:
                lines.append(f"           → {desc}")
        return "\n".join(lines)

    def _hash_tool(self, task: str) -> str:
        """Generate sample hashes for demonstration."""
        sample = "skytech45-ai-agent"
        results = [f"Hash Demo (input: \"{sample}\"):", "-" * 40]
        for algo in ["md5", "sha1", "sha256", "sha512"]:
            h = hashlib.new(algo, sample.encode()).hexdigest()
            results.append(f"  {algo.upper():8s} : {h}")
        return "\n".join(results)

    def _password_audit(self, task: str) -> str:
        """Quick password policy audit advice."""
        return (
            "Password Security Audit Recommendations\n"
            "─────────────────────────────────────────\n"
            "  ✅ Minimum 12 characters\n"
            "  ✅ Mix uppercase + lowercase + digits + symbols\n"
            "  ✅ No dictionary words or common patterns\n"
            "  ✅ Unique per account — use a password manager\n"
            "  ✅ Enable 2FA wherever possible\n"
            "  ❌ Never reuse passwords across sites\n"
            "  ❌ Never store passwords in plaintext\n"
            "\nTools: pass password_checker.py -p <password>"
        )

    def _subdomain_info(self, task: str) -> str:
        """Provide subdomain enumeration guidance."""
        return (
            "Subdomain Enumeration Guide\n"
            "─────────────────────────────────────────\n"
            "  Usage: python subdomain_finder.py -d target.com\n"
            "  Method: DNS resolution (passive, no brute-force traffic)\n"
            "  Output: resolved subdomains with IP addresses\n"
            "\n  ⚠️  Only enumerate domains you own or have permission for."
        )

    def _generic_security_advice(self, task: str) -> str:
        return (
            f"Security Analysis Request: {task}\n"
            "─────────────────────────────────────────\n"
            "  Use specific commands:\n"
            "  • port scan  → python main.py run --task \'scan ports on localhost\'\n"
            "  • headers    → python main.py run --task \'analyze headers https://site.com\'\n"
            "  • password   → python main.py run --task \'audit password strength\'\n"
        )
