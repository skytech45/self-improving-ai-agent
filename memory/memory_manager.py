"""
memory/memory_manager.py
Unified memory manager for the AI Agent System.
Handles short-term context, long-term JSON persistence,
and failure/success logging for the self-improvement engine.
"""

import json
import os
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryManager:
    """
    Manages all memory layers for the agent system.

    Memory layers:
    1. Short-term: in-memory dict (cleared each session)
    2. Long-term:  persisted JSON file (survives restarts)
    3. Failure log: structured log of failed tasks + errors
    4. Success log: structured log of successful task runs
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config       = config or {}
        self.persist_path = Path(self.config.get("persist_path", "memory/store"))
        self.max_short    = self.config.get("short_term_size", 100)

        # In-memory short-term store
        self._short_term: Dict[str, Any] = {}
        self._short_term_queue: deque    = deque(maxlen=self.max_short)

        # Persistent paths
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self._long_term_path = self.persist_path / "long_term.json"
        self._failure_log    = self.persist_path / "failures.jsonl"
        self._success_log    = self.persist_path / "successes.jsonl"

        # Load long-term memory
        self._long_term: Dict[str, Any] = self._load_long_term()

    # ── Short-term memory ─────────────────────────────────────────
    def store_short_term(self, key: str, value: Any) -> None:
        """Store a key-value pair in short-term memory."""
        if key not in self._short_term:
            self._short_term_queue.append(key)
        self._short_term[key] = value

    def get_short_term(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from short-term memory."""
        return self._short_term.get(key, default)

    def clear_short_term(self) -> None:
        """Clear all short-term memory."""
        self._short_term.clear()
        self._short_term_queue.clear()

    # ── Long-term memory ──────────────────────────────────────────
    def store_long_term(self, key: str, value: Any) -> None:
        """Persist a key-value pair to long-term memory."""
        self._long_term[key] = {
            "value": value,
            "timestamp": datetime.utcnow().isoformat()
        }
        self._save_long_term()

    def get_long_term(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from long-term memory."""
        entry = self._long_term.get(key)
        return entry["value"] if entry else default

    def _load_long_term(self) -> Dict[str, Any]:
        """Load long-term memory from disk."""
        if self._long_term_path.exists():
            try:
                with open(self._long_term_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_long_term(self) -> None:
        """Persist long-term memory to disk."""
        with open(self._long_term_path, "w") as f:
            json.dump(self._long_term, f, indent=2)

    # ── Failure / Success logging ─────────────────────────────────
    def log_failure(self, task: str, agent: str, error: str) -> None:
        """Log a failed task execution."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task":      task,
            "agent":     agent,
            "error":     error,
        }
        with open(self._failure_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_success(self, task: str, agent: str) -> None:
        """Log a successful task execution."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task":      task,
            "agent":     agent,
        }
        with open(self._success_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_recent_failures(self, n: int = 10) -> List[Dict]:
        """Return last N failure log entries."""
        return self._read_jsonl(self._failure_log, n)

    def get_recent_successes(self, n: int = 10) -> List[Dict]:
        """Return last N success log entries."""
        return self._read_jsonl(self._success_log, n)

    @staticmethod
    def _read_jsonl(path: Path, n: int) -> List[Dict]:
        """Read last N lines from a JSONL log file."""
        if not path.exists():
            return []
        lines = []
        try:
            with open(path, "r") as f:
                lines = f.readlines()
        except IOError:
            return []
        recent = lines[-n:] if len(lines) > n else lines
        result = []
        for line in recent:
            try:
                result.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                pass
        return result

    # ── Stats ─────────────────────────────────────────────────────
    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate memory statistics."""
        failures = self._read_jsonl(self._failure_log, 10000)
        successes = self._read_jsonl(self._success_log, 10000)
        return {
            "tasks_run":    len(failures) + len(successes),
            "successes":    len(successes),
            "failures":     len(failures),
            "improvements": self.get_long_term("improvements_applied", 0),
            "short_term_keys": len(self._short_term),
            "long_term_keys":  len(self._long_term),
        }
