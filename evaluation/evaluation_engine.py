"""
evaluation/evaluation_engine.py

Evaluation System — measures and tracks system performance.
Defines metrics, benchmarks, and scoring for all agent tasks.
Regression detection prevents deploying performance regressions.
"""
from __future__ import annotations

import json
import time
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger


@dataclass
class Metric:
    """A single performance metric data point."""
    name:      str
    value:     float
    unit:      str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    context:   Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of running the benchmark suite."""
    benchmark_id:   str
    total_tasks:    int
    passed:         int
    failed:         int
    avg_latency_ms: float
    success_rate:   float
    security_score: float
    overall_score:  float
    timestamp:      str = field(default_factory=lambda: datetime.utcnow().isoformat())
    details:        List[Dict] = field(default_factory=list)

    def is_regression(self, baseline: "BenchmarkResult", threshold: float = 0.05) -> bool:
        """Return True if this result is worse than baseline by > threshold."""
        return (
            self.overall_score < baseline.overall_score - threshold or
            self.success_rate  < baseline.success_rate  - threshold
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id":   self.benchmark_id,
            "total_tasks":    self.total_tasks,
            "passed":         self.passed,
            "failed":         self.failed,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "success_rate":   round(self.success_rate, 4),
            "security_score": round(self.security_score, 4),
            "overall_score":  round(self.overall_score, 4),
            "timestamp":      self.timestamp,
        }


# ── Benchmark Task Suite ───────────────────────────────────────────────────────
CODING_BENCHMARKS = [
    {"id": "cb_001", "task": "write a python function to binary search a sorted list",   "expected_keywords": ["def ", "mid", "return"], "category": "coding"},
    {"id": "cb_002", "task": "implement a class for a stack data structure",              "expected_keywords": ["class ", "def push", "def pop"], "category": "coding"},
    {"id": "cb_003", "task": "write a cli tool that reads a file and counts word freq",  "expected_keywords": ["argparse", "open(", "dict"], "category": "coding"},
    {"id": "cb_004", "task": "create a fastapi endpoint for user registration",          "expected_keywords": ["FastAPI", "@app.post", "BaseModel"], "category": "web"},
    {"id": "cb_005", "task": "implement password strength checker with entropy",         "expected_keywords": ["def ", "entropy", "score"], "category": "security"},
]

SECURITY_BENCHMARKS = [
    {"id": "sb_001", "task": "scan open ports on localhost",            "expected_keywords": ["port", "open", "127.0.0.1"], "category": "security"},
    {"id": "sb_002", "task": "analyze http security headers for a site","expected_keywords": ["Content-Security-Policy", "X-Frame"], "category": "security"},
    {"id": "sb_003", "task": "generate sha256 hash",                    "expected_keywords": ["sha256", "hexdigest"], "category": "security"},
]

ALL_BENCHMARKS = CODING_BENCHMARKS + SECURITY_BENCHMARKS


class EvaluationEngine:
    """
    Evaluation and benchmarking system.

    Responsibilities:
    - Run benchmark suites against live agents
    - Track historical performance metrics
    - Detect regressions before deployment
    - Score improvements vs baseline
    - Maintain persistent evaluation history
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config   = config or {}
        self.logger   = get_logger("EvaluationEngine")
        self.store    = Path(self.config.get("eval_store", "evaluation/history"))
        self.store.mkdir(parents=True, exist_ok=True)
        self._metrics: List[Metric] = []

    def run_benchmark(self, agents: Dict[str, Any]) -> BenchmarkResult:
        """
        Run full benchmark suite against provided agents.

        Args:
            agents: Dict mapping agent_key -> agent instance with execute() method

        Returns:
            BenchmarkResult with aggregate scores
        """
        import uuid
        bench_id = str(uuid.uuid4())[:8]
        self.logger.info(f"Starting benchmark [{bench_id}] — {len(ALL_BENCHMARKS)} tasks")

        details    = []
        latencies  = []
        passed     = 0

        for task_def in ALL_BENCHMARKS:
            start   = time.time()
            agent   = self._route_agent(task_def["task"], agents)
            result  = agent.execute(task_def["task"])
            elapsed = (time.time() - start) * 1000  # ms
            latencies.append(elapsed)

            output    = result.output.lower()
            keywords  = task_def["expected_keywords"]
            kw_hits   = sum(1 for kw in keywords if kw.lower() in output)
            task_pass = kw_hits >= len(keywords) * 0.6 and result.passed

            if task_pass:
                passed += 1

            details.append({
                "id":           task_def["id"],
                "category":     task_def["category"],
                "passed":       task_pass,
                "kw_hits":      kw_hits,
                "kw_total":     len(keywords),
                "latency_ms":   round(elapsed, 2),
                "confidence":   result.confidence,
            })

        total         = len(ALL_BENCHMARKS)
        success_rate  = passed / total if total else 0.0
        avg_latency   = statistics.mean(latencies) if latencies else 0.0
        sec_results   = [d for d in details if d["category"] == "security"]
        sec_score     = (sum(1 for d in sec_results if d["passed"]) / len(sec_results)
                         if sec_results else 1.0)
        overall       = (success_rate * 0.5 + sec_score * 0.3 +
                         min(1.0, 500.0 / avg_latency) * 0.2 if avg_latency else 0.0)

        bench = BenchmarkResult(
            benchmark_id   = bench_id,
            total_tasks    = total,
            passed         = passed,
            failed         = total - passed,
            avg_latency_ms = avg_latency,
            success_rate   = success_rate,
            security_score = sec_score,
            overall_score  = round(overall, 4),
            details        = details,
        )

        self._save_benchmark(bench)
        self.logger.info(
            f"Benchmark done — success={success_rate:.1%} "
            f"latency={avg_latency:.0f}ms score={overall:.3f}"
        )
        return bench

    def detect_regression(
        self,
        current: BenchmarkResult,
        baseline_n: int = 3,
    ) -> Tuple[bool, Optional[str]]:
        """
        Compare current benchmark against average of last N baselines.

        Args:
            current:    Latest benchmark result
            baseline_n: Number of historical results to average

        Returns:
            (is_regression, reason_string)
        """
        history = self._load_history(baseline_n)
        if not history:
            self.logger.info("No baseline history — skip regression check.")
            return False, None

        baseline_scores = [h.overall_score for h in history]
        baseline_avg    = statistics.mean(baseline_scores)
        threshold       = self.config.get("regression_threshold", 0.05)

        if current.overall_score < baseline_avg - threshold:
            reason = (
                f"Regression: score {current.overall_score:.3f} < "
                f"baseline {baseline_avg:.3f} (threshold {threshold})"
            )
            self.logger.warning(reason)
            return True, reason

        return False, None

    def record_metric(self, name: str, value: float, unit: str = "",
                      context: Dict[str, Any] = None) -> None:
        """Record a single performance metric."""
        m = Metric(name=name, value=value, unit=unit, context=context or {})
        self._metrics.append(m)
        metric_file = self.store / "metrics.jsonl"
        with open(metric_file, "a") as f:
            f.write(json.dumps({
                "name": m.name, "value": m.value, "unit": m.unit,
                "timestamp": m.timestamp, "context": m.context
            }) + "\n")

    def get_summary(self, last_n: int = 5) -> Dict[str, Any]:
        """Return performance summary from last N benchmarks."""
        history = self._load_history(last_n)
        if not history:
            return {"status": "no_history", "benchmarks": 0}
        scores   = [h.overall_score for h in history]
        success  = [h.success_rate  for h in history]
        latency  = [h.avg_latency_ms for h in history]
        return {
            "benchmarks":       len(history),
            "avg_score":        round(statistics.mean(scores), 3),
            "avg_success_rate": round(statistics.mean(success), 3),
            "avg_latency_ms":   round(statistics.mean(latency), 1),
            "trend":            "improving" if len(scores) > 1 and scores[-1] > scores[0] else "stable",
            "latest":           history[-1].to_dict() if history else None,
        }

    @staticmethod
    def _route_agent(task: str, agents: Dict[str, Any]) -> Any:
        """Simple routing to pick best agent for benchmark task."""
        t = task.lower()
        if any(k in t for k in ["port", "hash", "header", "password", "scan"]):
            return agents.get("security", list(agents.values())[0])
        if any(k in t for k in ["fastapi", "endpoint", "html", "api"]):
            return agents.get("web", list(agents.values())[0])
        return agents.get("coding", list(agents.values())[0])

    def _save_benchmark(self, bench: BenchmarkResult) -> None:
        path = self.store / f"bench_{bench.benchmark_id}.json"
        with open(path, "w") as f:
            json.dump(bench.to_dict(), f, indent=2)

    def _load_history(self, n: int) -> List[BenchmarkResult]:
        files = sorted(self.store.glob("bench_*.json"))[-n:]
        results = []
        for f in files:
            try:
                data = json.loads(f.read_text())
                results.append(BenchmarkResult(**{
                    k: v for k, v in data.items() if k != "details"
                }, details=[]))
            except Exception:
                pass
        return results
