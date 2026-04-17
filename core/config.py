"""
core/config.py
Configuration loader for the AI Agent System.
Supports YAML config files with environment variable overrides.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict


DEFAULTS: Dict[str, Any] = {
    "llm": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 2048,
    },
    "memory": {
        "short_term_size": 100,
        "vector_db": "faiss",
        "persist_path": "memory/store",
    },
    "github": {
        "repo": "",
        "branch": "main",
        "auto_push": True,
        "tag_stable": True,
    },
    "validation": {
        "run_linting": True,
        "run_tests": True,
        "run_security_scan": True,
        "sandbox_timeout": 30,
    },
    "improvement": {
        "cycle_interval_hours": 24,
        "max_candidates_per_cycle": 3,
        "min_test_pass_rate": 0.90,
    },
    "security": {
        "sandbox_mode": True,
        "allow_network": False,
        "max_exec_time": 30,
    }
}


def load_config(config_path: str = "configs/config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file, falling back to defaults.
    Environment variables override file values using prefix AIAGENT_.

    Example env override: AIAGENT_LLM_MODEL=gpt-4o

    Args:
        config_path: Path to YAML config file

    Returns:
        Merged configuration dictionary
    """
    config = dict(DEFAULTS)

    path = Path(config_path)
    if path.exists():
        with open(path, "r") as f:
            file_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, file_config)

    # Environment variable overrides
    config = _apply_env_overrides(config)

    return config


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base dict."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _apply_env_overrides(config: dict, prefix: str = "AIAGENT") -> dict:
    """Apply environment variable overrides (AIAGENT_SECTION_KEY=value)."""
    for key, value in os.environ.items():
        if key.startswith(f"{prefix}_"):
            parts = key[len(prefix)+1:].lower().split("_", 1)
            if len(parts) == 2:
                section, field = parts
                if section in config and isinstance(config[section], dict):
                    config[section][field] = _cast_value(value)
    return config


def _cast_value(value: str) -> Any:
    """Auto-cast string env var to appropriate Python type."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value
