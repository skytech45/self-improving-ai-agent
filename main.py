#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║          SELF-IMPROVING AI AGENT SYSTEM — main.py               ║
║  Author  : skytech45                                             ║
║  Version : 1.0.0                                                 ║
║  License : MIT                                                   ║
╚══════════════════════════════════════════════════════════════════╝

Entry point for the Self-Improving AI Agent System.
Orchestrates all subsystems: core engine, skill agents, memory,
self-improvement loop, validation pipeline, and GitHub automation.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.engine import AgentEngine
from core.config import load_config
from scheduler.task_scheduler import TaskScheduler
from utils.logger import setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Self-Improving AI Agent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  run       Start the agent in interactive or autonomous mode
  improve   Trigger the self-improvement cycle manually
  validate  Run the validation pipeline only
  schedule  Start the background task scheduler
  status    Show system status and last run stats

Examples:
  python main.py run --task "scan open ports on localhost"
  python main.py improve
  python main.py schedule --interval 24
  python main.py status
        """
    )
    parser.add_argument("mode", choices=["run", "improve", "validate", "schedule", "status"],
                        help="Operating mode")
    parser.add_argument("--task", type=str, default=None,
                        help="Task description for run mode")
    parser.add_argument("--config", type=str, default="configs/config.yaml",
                        help="Path to config file (default: configs/config.yaml)")
    parser.add_argument("--interval", type=int, default=24,
                        help="Scheduler interval in hours (default: 24)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate actions without making changes")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging")
    return parser.parse_args()


def main():
    args = parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger("main", log_level)

    logger.info("=" * 60)
    logger.info("  Self-Improving AI Agent System — Starting Up")
    logger.info("=" * 60)

    # Load configuration
    try:
        config = load_config(args.config)
        logger.info(f"Config loaded from: {args.config}")
    except FileNotFoundError:
        logger.warning(f"Config not found at {args.config}, using defaults.")
        config = {}

    # Initialize core engine
    engine = AgentEngine(config=config, dry_run=args.dry_run)

    if args.mode == "run":
        if not args.task:
            logger.error("--task required for run mode.")
            sys.exit(1)
        logger.info(f"Task: {args.task}")
        result = engine.run_task(args.task)
        print("\n" + "=" * 60)
        print("RESULT:")
        print(result)
        print("=" * 60)

    elif args.mode == "improve":
        logger.info("Triggering self-improvement cycle...")
        engine.run_improvement_cycle()

    elif args.mode == "validate":
        logger.info("Running validation pipeline...")
        engine.run_validation()

    elif args.mode == "schedule":
        logger.info(f"Starting scheduler (interval: {args.interval}h)")
        scheduler = TaskScheduler(engine, interval_hours=args.interval)
        scheduler.start()

    elif args.mode == "status":
        engine.show_status()


if __name__ == "__main__":
    main()
