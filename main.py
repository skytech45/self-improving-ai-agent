#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║       SELF-IMPROVING AI AGENT SYSTEM — main.py v2.0             ║
║  Author  : skytech45                                             ║
║  Version : 2.0.0  (production-grade, research-level)            ║
╚══════════════════════════════════════════════════════════════════╝

Entry point. Wires all subsystems together and exposes CLI interface.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.config import load_config
from memory.memory_manager import MemoryManager
from agents.builder_agent import BuilderAgent
from agents.critic_agent import CriticAgent
from agents.security_agent import SecurityAgent
from agents.optimizer_agent import OptimizerAgent
from agents.consensus import ConsensusEngine
from validation.validator import ValidationPipeline
from security.scanner import SecurityScanner
from evaluation.evaluation_engine import EvaluationEngine
from benchmarks.benchmark_suite import BenchmarkRunner
from github.git_manager import GitManager
from self_improvement.improvement_engine import ImprovementEngine
from orchestration.orchestrator import Orchestrator, TaskPriority
from orchestration.task_planner import TaskPlanner
from orchestration.tool_controller import ToolController
from scheduler.task_scheduler import TaskScheduler
from utils.logger import get_logger


VERSION = "2.0.0"


def build_system(config: dict, dry_run: bool = False) -> dict:
    """
    Wire all subsystems and return the component registry.
    This is the application factory / dependency injection root.
    """
    logger = get_logger("SystemFactory")
    logger.info(f"Building system v{VERSION} (dry_run={dry_run})")

    # Memory
    memory = MemoryManager(config=config.get("memory", {}))

    # Agents
    builder   = BuilderAgent(memory=memory, config=config.get("agents", {}).get("coding", {}))
    critic    = CriticAgent(memory=memory)
    security  = SecurityAgent(memory=memory, config=config.get("agents", {}).get("security", {}))
    optimizer = OptimizerAgent(memory=memory)
    consensus = ConsensusEngine(threshold=config.get("consensus", {}).get("threshold", 0.65))

    agents = {
        "coding":   builder,
        "web":      builder,
        "security": security,
    }

    # Infrastructure
    validator  = ValidationPipeline(config=config.get("validation", {}))
    scanner    = SecurityScanner(config=config.get("security", {}))
    evaluator  = EvaluationEngine(config=config.get("evaluation", {}))
    benchmarks = BenchmarkRunner(config=config.get("benchmarks", {}))
    git        = GitManager(config=config.get("github", {}), dry_run=dry_run)

    # Orchestration
    planner    = TaskPlanner()
    tool_ctrl  = ToolController()
    tool_ctrl.register("coding_agent",      lambda task: builder.execute(task).output)
    tool_ctrl.register("web_agent",         lambda task: builder.execute(task).output)
    tool_ctrl.register("security_agent",    lambda task: security.execute(task).output)
    tool_ctrl.register("multi_agent_debate",
                       lambda task: _multi_agent(task, builder, critic, security, optimizer, consensus))

    orchestrator = Orchestrator(
        memory=memory,
        tool_controller=tool_ctrl,
        planner=planner,
        config=config.get("orchestration", {}),
    )

    # Self-improvement
    improver = ImprovementEngine(
        memory=memory, git=git, validator=validator,
        evaluator=evaluator, agents=agents,
        config=config.get("improvement", {}),
    )

    logger.info("All subsystems wired.")
    return {
        "memory": memory, "builder": builder, "critic": critic,
        "security": security, "optimizer": optimizer, "consensus": consensus,
        "validator": validator, "scanner": scanner, "evaluator": evaluator,
        "benchmarks": benchmarks, "git": git, "orchestrator": orchestrator,
        "improver": improver, "agents": agents,
    }


def _multi_agent(task, builder, critic, security, optimizer, consensus) -> str:
    """Run multi-agent debate pipeline and return consensus result."""
    br  = builder.timed_execute(task)
    crs = [critic.critique(br), security.critique(br), optimizer.critique(br)]
    cr  = consensus.evaluate(br, crs)
    return (
        f"CONSENSUS: {'APPROVED' if cr.approved else 'REJECTED'} "
        f"(score={cr.consensus_score:.3f})\n\n"
        f"{cr.final_output}\n\n"
        f"Issues: {len(cr.all_issues)} | Suggestions: {len(cr.all_suggestions)}"
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=f"Self-Improving AI Agent System v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  run       Execute a task through the full multi-agent pipeline
  debate    Run multi-agent debate on a task (Builder+Critic+Security+Optimizer)
  improve   Trigger controlled self-improvement cycle
  benchmark Run the formal benchmark suite
  scan      Security scan a file or directory
  validate  Validate a Python file through the validation pipeline
  status    Show system status and memory stats

Examples:
  python main.py run --task "write a binary search function"
  python main.py debate --task "design a rate limiter"
  python main.py improve --dry-run
  python main.py benchmark
  python main.py scan --target agents/builder_agent.py
  python main.py validate --file agents/builder_agent.py
  python main.py status
        """
    )
    p.add_argument("mode",
        choices=["run","debate","improve","benchmark","scan","validate","schedule","status"])
    p.add_argument("--task",     type=str, help="Task description for run/debate mode")
    p.add_argument("--target",   type=str, help="File or directory path for scan mode")
    p.add_argument("--file",     type=str, help="Python file for validate mode")
    p.add_argument("--config",   type=str, default="configs/config.yaml")
    p.add_argument("--interval", type=int, default=24, help="Scheduler interval (hours)")
    p.add_argument("--dry-run",  action="store_true")
    p.add_argument("--verbose",  action="store_true")
    p.add_argument("--json",     action="store_true", help="Output results as JSON")
    return p.parse_args()


def main() -> None:
    args   = parse_args()
    level  = logging.DEBUG if args.verbose else logging.INFO
    logger = get_logger("main", level)

    logger.info("=" * 60)
    logger.info(f"  Self-Improving AI Agent System v{VERSION}")
    logger.info("=" * 60)

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        logger.warning(f"Config not found at {args.config} — using defaults.")
        config = {}

    sys_components = build_system(config, dry_run=args.dry_run)

    if args.mode == "run":
        if not args.task:
            print("[ERROR] --task required for run mode."); sys.exit(1)
        ctx = sys_components["orchestrator"].execute(args.task)
        if args.json:
            print(json.dumps(ctx.to_dict(), indent=2))
        else:
            print("\n" + "=" * 60)
            print(f"RESULT ({ctx.status.value}) [{ctx.elapsed}s]:")
            print(ctx.result or ctx.error)
            print("=" * 60)

    elif args.mode == "debate":
        if not args.task:
            print("[ERROR] --task required for debate mode."); sys.exit(1)
        sc = sys_components
        result = _multi_agent(
            args.task, sc["builder"], sc["critic"],
            sc["security"], sc["optimizer"], sc["consensus"]
        )
        print("\n" + result)

    elif args.mode == "improve":
        summary = sys_components["improver"].run_cycle(dry_run=args.dry_run)
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"\nImprovement cycle complete:")
            for k, v in summary.items():
                print(f"  {k:<20}: {v}")

    elif args.mode == "benchmark":
        runner = sys_components["benchmarks"]
        result = runner.run(sys_components["agents"])
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(runner.format_report(result))

    elif args.mode == "scan":
        target  = args.target or "."
        scanner = sys_components["scanner"]
        if Path(target).is_file():
            code   = Path(target).read_text(encoding="utf-8")
            report = scanner.scan_code(code, target)
        else:
            report = scanner.scan_directory(target)
        if args.json:
            print(json.dumps(report.summary(), indent=2))
        else:
            print(scanner.format_report(report))

    elif args.mode == "validate":
        if not args.file:
            print("[ERROR] --file required for validate mode."); sys.exit(1)
        result = sys_components["validator"].validate_file(args.file)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status = "PASSED" if result["passed"] else "FAILED"
            print(f"\nValidation {status}")
            for stage, data in result.get("stages", {}).items():
                mark = "PASS" if data.get("passed") else "FAIL"
                print(f"  [{mark}] {stage}")
            if result.get("errors"):
                print("  Errors:", result["errors"])

    elif args.mode == "schedule":
        logger.info(f"Starting scheduler (interval={args.interval}h)")
        scheduler = TaskScheduler(sys_components["improver"], args.interval)
        scheduler.start()

    elif args.mode == "status":
        stats = sys_components["memory"].get_stats()
        print("\n" + "=" * 55)
        print(f"  SYSTEM STATUS — v{VERSION}")
        print("=" * 55)
        for k, v in stats.items():
            print(f"  {k:<28}: {v}")
        print("=" * 55)


if __name__ == "__main__":
    main()
