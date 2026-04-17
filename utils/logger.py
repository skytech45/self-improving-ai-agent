"""
utils/logger.py

Centralized logging factory.
All modules call get_logger(name) — consistent format + file output.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_loggers: dict = {}


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get or create a named logger with console + daily file handlers.

    Args:
        name:  Logger name (module / class)
        level: Log level (default: INFO)

    Returns:
        Configured Logger instance (cached — no duplicate handlers)
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        fmt = logging.Formatter(
            "%(asctime)s | %(name)-22s | %(levelname)-7s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

        # Daily rotating file
        today    = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = LOG_DIR / f"agent_{today}.log"
        fh       = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    _loggers[name] = logger
    return logger


# Legacy alias for backwards compatibility
def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    return get_logger(name, level)
