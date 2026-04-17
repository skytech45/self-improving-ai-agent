"""
memory/memory_manager.py

Hybrid Memory Manager — four memory layers:
1. Short-term  : in-process dict (session-scoped)
2. Long-term   : JSON persistence (survives restarts)
3. Episodic    : task history with full context
4. Failure     : structured failure + correction log
"""
from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger


@dataclass
class EpisodicEntry:
    """A single task episode stored in episodic memory."""
    task:       str
    agent:      str
    result:     str
    success:    bool
    elapsed_s:  float
    timestamp:  str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata:   Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureEntry:
    """Structured failure log entry with correction tracking."""
    task:       str
    agent:      str
    error:      str
    correction: str = ""
    resolved:   bool = False
    timestamp:  str = field(default_factory=lambda: datetime.utcnow().isoformat())


class MemoryManager:
    """
    Hybrid memory manager for the AI Agent System.

    Layer summary:
    ┌─────────────┬────────────────────────┬──────────────────┐
    │ Layer       │ Scope                  │ Storage          │
    ├─────────────┼────────────────────────┼──────────────────┤
    │ Short-term  │ Current session        │ In-memory dict   │
    │ Long-term   │ Cross-session facts    │ JSON file        │
    │ Episodic    │ Task history           │ JSONL file       │
    │ Failure     │ Failures + corrections │ JSONL file       │
    └─────────────┴────────────────────────┴──────────────────┘
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config    = config or {}
        self.logger    = get_logger("MemoryManager")
        self.store     = Path(self.config.get("persist_path", "memory/store"))
        self.max_short = self.config.get("short_term_size", 200)
        self.store.mkdir(parents=True, exist_ok=True)

        # Layer 1: Short-term
        self._short:  Dict[str, Any] = {}
        self._short_q: deque         = deque(maxlen=self.max_short)

        # Layer 2: Long-term (JSON)
        self._lt_path  = self.store / "long_term.json"
        self._long:  Dict[str, Any] = self._load_json(self._lt_path, {})

        # Layer 3 & 4: Episodic + Failure (JSONL append-only)
        self._ep_path  = self.store / "episodic.jsonl"
        self._fail_path = self.store / "failures.jsonl"
        self._succ_path = self.store / "successes.jsonl"

        self.logger.info(
            f"MemoryManager ready — "
            f"long_term_keys={len(self._long)} store={self.store}"
        )

    # ── Short-term ────────────────────────────────────────────────

    def store_short_term(self, key: str, value: Any) -> None:
        if key not in self._short:
            self._short_q.append(key)
        self._short[key] = value

    def get_short_term(self, key: str, default: Any = None) -> Any:
        return self._short.get(key, default)

    def clear_short_term(self) -> None:
        self._short.clear()
        self._short_q.clear()
        self.logger.debug("Short-term memory cleared.")

    # ── Long-term ─────────────────────────────────────────────────

    def store_long_term(self, key: str, value: Any) -> None:
        self._long[key] = {
            "value":     value,
            "updated":   datetime.utcnow().isoformat(),
        }
        self._save_json(self._lt_path, self._long)

    def get_long_term(self, key: str, default: Any = None) -> Any:
        entry = self._long.get(key)
        return entry["value"] if entry else default

    # ── Episodic ──────────────────────────────────────────────────

    def log_episode(
        self,
        task:      str,
        agent:     str,
        result:    str,
        success:   bool,
        elapsed_s: float = 0.0,
        metadata:  Dict[str, Any] = None,
    ) -> None:
        """Record a full task episode."""
        ep = EpisodicEntry(
            task=task, agent=agent, result=result[:200],
            success=success, elapsed_s=elapsed_s, metadata=metadata or {}
        )
        self._append_jsonl(self._ep_path, asdict(ep))

    def get_recent_episodes(self, n: int = 20) -> List[Dict]:
        return self._tail_jsonl(self._ep_path, n)

    # ── Failure + Success ─────────────────────────────────────────

    def log_failure(
        self,
        task:      str,
        agent:     str,
        error:     str,
        correction: str = "",
    ) -> None:
        entry = FailureEntry(task=task, agent=agent, error=error, correction=correction)
        self._append_jsonl(self._fail_path, asdict(entry))

    def log_success(self, task: str, agent: str, elapsed_s: float = 0.0) -> None:
        self._append_jsonl(self._succ_path, {
            "task":      task[:120],
            "agent":     agent,
            "elapsed_s": elapsed_s,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_recent_failures(self, n: int = 50) -> List[Dict]:
        return self._tail_jsonl(self._fail_path, n)

    def get_recent_successes(self, n: int = 50) -> List[Dict]:
        return self._tail_jsonl(self._succ_path, n)

    def mark_failure_resolved(self, task_prefix: str, correction: str) -> int:
        """Mark matching failures as resolved with a correction note. Returns count updated."""
        failures = self._tail_jsonl(self._fail_path, 1000)
        updated  = 0
        for f in failures:
            if task_prefix.lower() in f.get("task", "").lower() and not f.get("resolved"):
                f["resolved"]   = True
                f["correction"] = correction
                updated += 1
        if updated:
            with open(self._fail_path, "w") as fl:
                for f in failures:
                    fl.write(json.dumps(f) + "\n")
        return updated

    # ── Stats ─────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        failures  = self._tail_jsonl(self._fail_path, 10000)
        successes = self._tail_jsonl(self._succ_path, 10000)
        episodes  = self._tail_jsonl(self._ep_path, 10000)
        return {
            "short_term_keys":    len(self._short),
            "long_term_keys":     len(self._long),
            "total_episodes":     len(episodes),
            "total_successes":    len(successes),
            "total_failures":     len(failures),
            "improvements_applied": self.get_long_term("improvements_applied", 0),
        }

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _load_json(path: Path, default: Any) -> Any:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return default

    @staticmethod
    def _save_json(path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def _append_jsonl(path: Path, entry: Dict) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    @staticmethod
    def _tail_jsonl(path: Path, n: int) -> List[Dict]:
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except IOError:
            return []
        result = []
        for line in lines[-n:]:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return result
