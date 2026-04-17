"""
orchestration/tool_controller.py

Tool Selection + Execution Controller.
Dispatches sub-tasks to registered tools/agents.
All dispatched calls are logged and timed.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, Dict, Optional

from utils.logger import get_logger


class ToolController:
    """
    Central dispatcher for all agent tools.

    Tools are registered by name. The controller:
    - Validates tool existence before dispatch
    - Times every execution
    - Catches and re-raises with context
    - Logs all invocations
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self.logger = get_logger("ToolController")

    def register(self, name: str, fn: Callable) -> None:
        """Register a callable under a tool name."""
        self._tools[name] = fn
        self.logger.debug(f"Tool registered: {name}")

    def dispatch(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Dispatch a call to a registered tool.

        Args:
            tool_name: Registered tool identifier
            args:      Arguments dict passed to the tool

        Returns:
            Tool result

        Raises:
            KeyError:   Unknown tool
            RuntimeError: Tool execution error
        """
        if tool_name not in self._tools:
            raise KeyError(f"Unknown tool: {tool_name!r}. Registered: {list(self._tools)}")

        self.logger.info(f"Dispatching: {tool_name} | args_keys={list(args)}")
        start = time.time()

        try:
            result = self._tools[tool_name](**args)
            elapsed = round(time.time() - start, 3)
            self.logger.info(f"Tool {tool_name} completed in {elapsed}s")
            return result
        except Exception as exc:
            elapsed = round(time.time() - start, 3)
            self.logger.error(f"Tool {tool_name} failed after {elapsed}s: {exc}")
            raise RuntimeError(f"Tool {tool_name!r} failed: {exc}") from exc

    def list_tools(self) -> list:
        return list(self._tools.keys())
