"""
benchmarks/benchmark_suite.py

Formal benchmark suite for the Self-Improving AI Agent System.
Provides reproducible, measurable tests for:
- Coding task correctness
- Security analysis accuracy
- Web scaffolding quality
- Response latency
- Regression detection
"""
from __future__ import annotations

import time
import statistics
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from utils.logger import get_logger


@dataclass
class BenchmarkCase:
    """A single benchmark test case."""
    case_id:          str
    category:         str           # coding | security | web | debug
    task:             str
    expected_keywords: List[str]
    min_confidence:   float = 0.50
    max_latency_ms:   float = 5000.0
    tags:             List[str] = field(default_factory=list)


@dataclass
class CaseResult:
    """Result of a single benchmark case execution."""
    case_id:      str
    passed:       bool
    latency_ms:   float
    confidence:   float
    kw_hit_rate:  float
    output_len:   int
    error:        str = ""


@dataclass
class SuiteResult:
    """Aggregate results from a full benchmark suite run."""
    run_id:         str
    timestamp:      str
    total:          int
    passed:         int
    failed:         int
    avg_latency_ms: float
    success_rate:   float
    category_scores: Dict[str, float] = field(default_factory=dict)
    case_results:   List[CaseResult]  = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        lat_score = min(1.0, 2000.0 / max(self.avg_latency_ms, 1.0))
        return round(self.success_rate * 0.70 + lat_score * 0.30, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id":          self.run_id,
            "timestamp":       self.timestamp,
            "total":           self.total,
            "passed":          self.passed,
            "success_rate":    round(self.success_rate, 4),
            "avg_latency_ms":  round(self.avg_latency_ms, 2),
            "overall_score":   self.overall_score,
            "category_scores": self.category_scores,
        }


# ── Official Benchmark Dataset ─────────────────────────────────────────────────
BENCHMARK_DATASET: List[BenchmarkCase] = [
    # Coding
    BenchmarkCase("C001", "coding",
        "write a python function to binary search a sorted list",
        ["def ", "mid", "return"], min_confidence=0.6),
    BenchmarkCase("C002", "coding",
        "implement a class for a stack data structure with push pop peek",
        ["class ", "def push", "def pop"], min_confidence=0.6),
    BenchmarkCase("C003", "coding",
        "write a cli script that reads a file and counts word frequencies",
        ["argparse", "open(", "dict"], min_confidence=0.5),
    BenchmarkCase("C004", "coding",
        "implement a function to validate an email address",
        ["def ", "re.", "return"], min_confidence=0.5),
    BenchmarkCase("C005", "coding",
        "create a python decorator for retry logic with exponential backoff",
        ["def ", "wrapper", "time"], min_confidence=0.5),
    # Web
    BenchmarkCase("W001", "web",
        "create a fastapi endpoint for user registration with validation",
        ["FastAPI", "@app.post", "BaseModel"], min_confidence=0.6),
    BenchmarkCase("W002", "web",
        "scaffold a flask api with get and post routes for items",
        ["Flask", "@app.route", "jsonify"], min_confidence=0.6),
    BenchmarkCase("W003", "web",
        "build a landing page html with navigation and hero section",
        ["<!DOCTYPE", "<nav", "<section"], min_confidence=0.5),
    # Security
    BenchmarkCase("S001", "security",
        "scan open ports on localhost",
        ["port", "open", "127.0.0.1"], min_confidence=0.7),
    BenchmarkCase("S002", "security",
        "analyze http security headers checklist",
        ["Content-Security-Policy", "X-Frame"], min_confidence=0.7),
    BenchmarkCase("S003", "security",
        "generate sha256 and md5 hash demonstration",
        ["SHA256", "MD5"], min_confidence=0.8),
    BenchmarkCase("S004", "security",
        "sql injection prevention best practices",
        ["parameterized", "injection", "ORM"], min_confidence=0.6),
]


class BenchmarkRunner:
    """
    Runs the formal benchmark suite against agent instances.

    Usage:
        runner = BenchmarkRunner()
        result = runner.run(agents_dict)
        print(runner.format_report(result))
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config  = config or {}
        self.logger  = get_logger("BenchmarkRunner")
        self.history = Path(self.config.get("history_path", "benchmarks/history"))
        self.history.mkdir(parents=True, exist_ok=True)

    def run(self, agents: Dict[str, Any]) -> SuiteResult:
        """
        Run all benchmark cases against the agent pool.

        Args:
            agents: Dict with keys like "coding", "web", "security"

        Returns:
            SuiteResult with aggregate metrics
        """
        import uuid
        run_id    = str(uuid.uuid4())[:8]
        self.logger.info(f"Benchmark run [{run_id}] — {len(BENCHMARK_DATASET)} cases")

        case_results: List[CaseResult] = []
        category_data: Dict[str, List[bool]] = {}

        for case in BENCHMARK_DATASET:
            cr = self._run_case(case, agents)
            case_results.append(cr)
            category_data.setdefault(case.category, []).append(cr.passed)

        passed     = sum(1 for r in case_results if r.passed)
        latencies  = [r.latency_ms for r in case_results]
        avg_lat    = statistics.mean(latencies) if latencies else 0.0
        succ_rate  = passed / len(case_results) if case_results else 0.0
        cat_scores = {
            cat: round(sum(v) / len(v), 3)
            for cat, v in category_data.items()
        }

        result = SuiteResult(
            run_id          = run_id,
            timestamp       = datetime.utcnow().isoformat(),
            total           = len(case_results),
            passed          = passed,
            failed          = len(case_results) - passed,
            avg_latency_ms  = avg_lat,
            success_rate    = succ_rate,
            category_scores = cat_scores,
            case_results    = case_results,
        )

        self._save(result)
        self.logger.info(
            f"Benchmark [{run_id}] done — "
            f"pass={succ_rate:.1%} lat={avg_lat:.0f}ms score={result.overall_score:.3f}"
        )
        return result

    def detect_regression(
        self,
        current:    SuiteResult,
        baseline_n: int = 3,
        threshold:  float = 0.05,
    ) -> tuple:
        """
        Compare current run to average of last N baseline runs.

        Returns:
            (is_regression: bool, reason: str)
        """
        history = self._load_history(baseline_n)
        if not history:
            return False, ""

        baseline_avg = statistics.mean(h["overall_score"] for h in history)
        if current.overall_score < baseline_avg - threshold:
            reason = (
                f"Regression: {current.overall_score:.3f} < "
                f"baseline {baseline_avg:.3f} (delta={threshold})"
            )
            return True, reason
        return False, ""

    def format_report(self, result: SuiteResult) -> str:
        """Human-readable benchmark report."""
        lines = [
            "=" * 60,
            f"  BENCHMARK REPORT — Run {result.run_id}",
            "=" * 60,
            f"  Date          : {result.timestamp[:19]}",
            f"  Total Cases   : {result.total}",
            f"  Passed        : {result.passed}/{result.total} ({result.success_rate:.1%})",
            f"  Avg Latency   : {result.avg_latency_ms:.0f}ms",
            f"  Overall Score : {result.overall_score:.3f}",
            "-" * 60,
            "  Category Scores:",
        ]
        for cat, score in result.category_scores.items():
            bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
            lines.append(f"  {cat:<12} [{bar}] {score:.1%}")
        lines.append("-" * 60)
        lines.append("  Case Results:")
        for cr in result.case_results:
            mark = "PASS" if cr.passed else "FAIL"
            lines.append(
                f"  [{mark}] {cr.case_id} | "
                f"conf={cr.confidence:.2f} lat={cr.latency_ms:.0f}ms"
            )
        lines.append("=" * 60)
        return "\n".join(lines)

    # ── Private ────────────────────────────────────────────────────

    def _run_case(self, case: BenchmarkCase, agents: Dict[str, Any]) -> CaseResult:
        agent = agents.get(case.category, agents.get("coding"))
        start = time.time()
        error = ""
        try:
            result     = agent.execute(case.task)
            output     = result.output.lower()
            confidence = result.confidence
            passed_flag = result.passed
        except Exception as e:
            output      = ""
            confidence  = 0.0
            passed_flag = False
            error       = str(e)[:100]

        elapsed   = (time.time() - start) * 1000
        kw_hits   = sum(1 for kw in case.expected_keywords if kw.lower() in output)
        kw_rate   = kw_hits / len(case.expected_keywords) if case.expected_keywords else 1.0
        passed    = (
            kw_rate >= 0.6
            and confidence >= case.min_confidence
            and elapsed <= case.max_latency_ms
            and passed_flag
            and not error
        )
        return CaseResult(
            case_id    = case.case_id,
            passed     = passed,
            latency_ms = round(elapsed, 2),
            confidence = confidence,
            kw_hit_rate = round(kw_rate, 3),
            output_len  = len(output),
            error       = error,
        )

    def _save(self, result: SuiteResult) -> None:
        path = self.history / f"bench_{result.run_id}.json"
        path.write_text(json.dumps(result.to_dict(), indent=2))

    def _load_history(self, n: int) -> List[Dict]:
        files = sorted(self.history.glob("bench_*.json"))[-n:]
        data  = []
        for f in files:
            try:
                data.append(json.loads(f.read_text()))
            except Exception:
                pass
        return data
