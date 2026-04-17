"""
utils/logger.py
Centralized logging setup for the AI Agent System.
All modules use this logger for consistent formatting and output.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Create and configure a named logger with console + file handlers.

    Args:
        name:  Logger name (usually module/class name)
        level: Logging level (default: INFO)

    Returns:
        Configured Logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler (daily rotating)
    today     = datetime.utcnow().strftime("%Y-%m-%d")
    log_file  = LOG_DIR / f"agent_{today}.log"
    file_hdlr = logging.FileHandler(log_file, encoding="utf-8")
    file_hdlr.setLevel(logging.DEBUG)
    file_hdlr.setFormatter(formatter)
    logger.addHandler(file_hdlr)

    return logger
