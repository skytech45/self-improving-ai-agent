"""
tools/file_tool.py

File system interface for the agent system.
Provides safe, sandboxed read/write operations within allowed paths.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional


ALLOWED_BASE = Path(".").resolve()  # Restrict to project root


class FileTool:
    """
    Safe file system interface.

    Security: all paths are resolved and validated against ALLOWED_BASE.
    No path traversal (../) is permitted.
    """

    def read(self, path: str) -> str:
        """Read a file and return its content."""
        safe = self._safe_path(path)
        return safe.read_text(encoding="utf-8")

    def write(self, path: str, content: str) -> bool:
        """Write content to a file. Returns True on success."""
        safe = self._safe_path(path)
        safe.parent.mkdir(parents=True, exist_ok=True)
        safe.write_text(content, encoding="utf-8")
        return True

    def exists(self, path: str) -> bool:
        return self._safe_path(path).exists()

    def list_dir(self, path: str = ".") -> list:
        return [str(p) for p in self._safe_path(path).iterdir()]

    @staticmethod
    def _safe_path(path: str) -> Path:
        resolved = (ALLOWED_BASE / path).resolve()
        if not str(resolved).startswith(str(ALLOWED_BASE)):
            raise PermissionError(f"Path traversal denied: {path!r}")
        return resolved
