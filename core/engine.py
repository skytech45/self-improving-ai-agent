"""
core/engine.py
Central orchestration engine for the AI Agent System.
Coordinates all subsystems: task planning, skill routing,
memory access, self-improvement, and GitHub automation.
"""

import logging
import time
from typing import Any, Dict, Optional

from agents.coding_agent import CodingAgent
from agents.web_agent import WebAgent
from agents.security_agent import SecurityAgent
from memory.memory_manager import MemoryManager
from self_improvement.improvement_engine import ImprovementEngine
from validation.validator import ValidationPipeline
from github.git_manager import GitManager
from utils.logger import setup_logger


class AgentEngine:
    """
    Central orchestration engine.
    Routes tasks to specialized skill agents, manages memory,
    and coordinates the self-improvement pipeline.
    """

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] = None, dry_run: bool = False):
        self.config    = config or {}
        self.dry_run   = dry_run
        self.logger    = setup_logger("AgentEngine")
        self.start_time = time.time()

        self.logger.info(f"Initializing AgentEngine v{self.VERSION} (dry_run={dry_run})")

        # Initialize subsystems
        self.memory      = MemoryManager(config=self.config.get("memory", {}))
        self.git         = GitManager(config=self.config.get("github", {}), dry_run=dry_run)
        self.validator   = ValidationPipeline(config=self.config.get("validation", {}))
        self.improver    = ImprovementEngine(
            memory=self.memory,
            git=self.git,
            validator=self.validator,
            config=self.config.get("improvement", {})
        )

        # Skill agents
        self.agents = {
            "coding":   CodingAgent(memory=self.memory, config=self.config.get("coding", {})),
            "web":      WebAgent(memory=self.memory, config=self.config.get("web", {})),
            "security": SecurityAgent(memory=self.memory, config=self.config.get("security", {})),
        }

        self.logger.info("All subsystems initialized.")

    def classify_task(self, task: str) -> str:
        """
        Route a task description to the appropriate skill agent.

        Simple keyword-based routing. Can be upgraded to LLM-based
        intent classification for more complex tasks.

        Args:
            task: Natural language task description

        Returns:
            Agent key: "coding", "web", or "security"
        """
        task_lower = task.lower()
        security_keywords = [
            "scan", "port", "vulnerability", "exploit", "pentest",
            "nmap", "subdomain", "header", "injection", "xss", "hash"
        ]
        web_keywords = [
            "website", "html", "css", "frontend", "backend", "api",
            "fastapi", "flask", "django", "javascript", "scaffold"
        ]
        coding_keywords = [
            "write", "code", "script", "function", "debug", "refactor",
            "optimize", "test", "implement", "class", "module"
        ]

        for kw in security_keywords:
            if kw in task_lower:
                return "security"
        for kw in web_keywords:
            if kw in task_lower:
                return "web"
        return "coding"  # default

    def run_task(self, task: str) -> str:
        """
        Execute a task using the appropriate skill agent.

        Args:
            task: Natural language task description

        Returns:
            Task result as string
        """
        self.logger.info(f"Received task: {task}")

        # Store in short-term memory
        self.memory.store_short_term("last_task", task)

        # Route to agent
        agent_key = self.classify_task(task)
        agent = self.agents[agent_key]
        self.logger.info(f"Routing to: {agent_key} agent")

        try:
            result = agent.execute(task)
            self.memory.store_short_term("last_result", result)
            self.memory.log_success(task, agent_key)
            return result
        except Exception as e:
            self.logger.error(f"Task failed: {e}")
            self.memory.log_failure(task, agent_key, str(e))
            return f"[ERROR] Task failed: {e}"

    def run_improvement_cycle(self) -> Dict[str, Any]:
        """
        Trigger the full self-improvement pipeline:
        1. Analyze logs and failures
        2. Generate improvement candidates
        3. Validate candidates
        4. Deploy if valid, rollback if not
        5. Commit to GitHub

        Returns:
            Summary dict of improvement results
        """
        self.logger.info("Starting self-improvement cycle...")
        return self.improver.run_cycle(dry_run=self.dry_run)

    def run_validation(self) -> Dict[str, Any]:
        """Run the validation pipeline on current codebase."""
        self.logger.info("Running validation pipeline...")
        return self.validator.run_full_validation(".")

    def show_status(self) -> None:
        """Print system status summary."""
        uptime = time.time() - self.start_time
        stats  = self.memory.get_stats()
        print("\n" + "=" * 55)
        print("  SELF-IMPROVING AI AGENT — STATUS")
        print("=" * 55)
        print(f"  Version    : {self.VERSION}")
        print(f"  Uptime     : {uptime:.1f}s")
        print(f"  Dry Run    : {self.dry_run}")
        print(f"  Tasks Run  : {stats.get('tasks_run', 0)}")
        print(f"  Successes  : {stats.get('successes', 0)}")
        print(f"  Failures   : {stats.get('failures', 0)}")
        print(f"  Improvements Applied: {stats.get('improvements', 0)}")
        print("=" * 55 + "\n")
