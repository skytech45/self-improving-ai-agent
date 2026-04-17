"""
self_improvement/improvement_engine.py
The Self-Improvement Engine — core of the autonomous evolution system.

Workflow:
1. Analyze failure logs and performance metrics
2. Generate improvement candidates (prompt / code / config)
3. Run through ValidationPipeline
4. Deploy if passed — commit to GitHub
5. Rollback if failed — log and abort
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ImprovementCandidate:
    """Represents a proposed improvement to the system."""

    def __init__(self, file_path: str, new_content: str,
                 reason: str, improvement_type: str):
        self.file_path        = file_path
        self.new_content      = new_content
        self.reason           = reason
        self.improvement_type = improvement_type  # refactor|feat|fix|docs
        self.timestamp        = datetime.utcnow().isoformat()
        self.validation_result: Optional[Dict] = None
        self.deployed         = False

    def to_dict(self) -> Dict:
        return {
            "file_path":        self.file_path,
            "reason":           self.reason,
            "improvement_type": self.improvement_type,
            "timestamp":        self.timestamp,
            "deployed":         self.deployed,
            "validation":       self.validation_result,
        }


class ImprovementEngine:
    """
    Autonomous self-improvement engine.
    Analyzes the agent system, generates candidate improvements,
    validates them, and safely deploys passing updates.
    """

    def __init__(self, memory, git, validator, config: Dict[str, Any] = None):
        self.memory    = memory
        self.git       = git
        self.validator = validator
        self.config    = config or {}
        self.logger    = logging.getLogger("ImprovementEngine")
        self.audit_log = Path("self_improvement/audit_log.jsonl")
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        self.max_candidates = self.config.get("max_candidates_per_cycle", 3)

    def run_cycle(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute one full self-improvement cycle.

        Returns:
            Summary: { analyzed, candidates, deployed, failed, skipped }
        """
        self.logger.info("=" * 50)
        self.logger.info("SELF-IMPROVEMENT CYCLE STARTED")
        self.logger.info("=" * 50)

        summary = {
            "cycle_start":  datetime.utcnow().isoformat(),
            "analyzed":     0,
            "candidates":   0,
            "deployed":     0,
            "failed":       0,
            "skipped":      0,
            "dry_run":      dry_run,
        }

        # Step 1: Analyze
        analysis = self._analyze_system()
        summary["analyzed"] = analysis["total_issues"]
        self.logger.info(f"Analysis: {analysis['total_issues']} issues found")

        if analysis["total_issues"] == 0:
            self.logger.info("System is healthy — no improvements needed.")
            self._write_audit(summary)
            return summary

        # Step 2: Generate candidates
        candidates = self._generate_candidates(analysis)
        summary["candidates"] = len(candidates)
        self.logger.info(f"Generated {len(candidates)} improvement candidate(s)")

        # Step 3: Validate + deploy each candidate
        for candidate in candidates[:self.max_candidates]:
            result = self._process_candidate(candidate, dry_run)
            if result == "deployed":
                summary["deployed"] += 1
            elif result == "failed":
                summary["failed"] += 1
            else:
                summary["skipped"] += 1

        # Step 4: Update stats
        total_improvements = self.memory.get_long_term("improvements_applied", 0)
        self.memory.store_long_term("improvements_applied",
                                    total_improvements + summary["deployed"])

        summary["cycle_end"] = datetime.utcnow().isoformat()
        self._write_audit(summary)

        self.logger.info(f"Cycle complete — deployed: {summary['deployed']}, "
                         f"failed: {summary['failed']}")
        return summary

    def _analyze_system(self) -> Dict[str, Any]:
        """
        Analyze agent system for improvement opportunities.
        Checks: failure rate, slow operations, missing docs.
        """
        issues = []
        failures = self.memory.get_recent_failures(50)
        successes = self.memory.get_recent_successes(50)

        # Check failure rate
        total = len(failures) + len(successes)
        if total > 0:
            failure_rate = len(failures) / total
            if failure_rate > 0.2:
                issues.append({
                    "type": "high_failure_rate",
                    "value": failure_rate,
                    "description": f"Failure rate {failure_rate:.1%} exceeds 20% threshold"
                })

        # Check for repeated errors
        error_counts: Dict[str, int] = {}
        for f in failures:
            err = f.get("error", "")[:80]
            error_counts[err] = error_counts.get(err, 0) + 1

        for err, count in error_counts.items():
            if count >= 3:
                issues.append({
                    "type": "repeated_error",
                    "value": count,
                    "description": f"Error repeated {count}x: {err}"
                })

        return {
            "total_issues":  len(issues),
            "issues":        issues,
            "failure_count": len(failures),
            "success_count": len(successes),
        }

    def _generate_candidates(self, analysis: Dict) -> List[ImprovementCandidate]:
        """Generate improvement candidates based on analysis results."""
        candidates = []

        for issue in analysis.get("issues", []):
            if issue["type"] == "high_failure_rate":
                candidates.append(ImprovementCandidate(
                    file_path="self_improvement/improvement_notes.md",
                    new_content=self._build_improvement_note(issue),
                    reason=issue["description"],
                    improvement_type="docs"
                ))
            elif issue["type"] == "repeated_error":
                candidates.append(ImprovementCandidate(
                    file_path="self_improvement/known_errors.json",
                    new_content=json.dumps({"known_errors": [issue]}, indent=2),
                    reason=issue["description"],
                    improvement_type="fix"
                ))

        return candidates

    def _process_candidate(self, candidate: ImprovementCandidate,
                            dry_run: bool) -> str:
        """
        Validate and deploy a single improvement candidate.

        Returns: "deployed" | "failed" | "skipped"
        """
        self.logger.info(f"Processing: {candidate.file_path} ({candidate.reason[:50]})")

        # Validate if it's Python code
        if candidate.file_path.endswith(".py"):
            result = self.validator.validate_code(
                candidate.new_content, candidate.file_path
            )
            candidate.validation_result = result
            if not result["passed"]:
                self.logger.warning(f"Validation FAILED: {result['errors']}")
                self._write_audit(candidate.to_dict(), event="validation_failed")
                return "failed"
        else:
            candidate.validation_result = {"passed": True, "stages": {}}

        # Deploy
        if dry_run:
            self.logger.info(f"[DRY RUN] Would deploy: {candidate.file_path}")
            return "skipped"

        try:
            path = Path(candidate.file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(candidate.new_content, encoding="utf-8")
            candidate.deployed = True

            # Commit to GitHub
            commit_msg = (f"{candidate.improvement_type}: "
                          f"auto-improvement — {candidate.reason[:60]}")
            self.git.commit_file(candidate.file_path, candidate.new_content, commit_msg)

            self.logger.info(f"✅ Deployed and committed: {candidate.file_path}")
            self._write_audit(candidate.to_dict(), event="deployed")
            return "deployed"

        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            self._write_audit({"error": str(e), "candidate": candidate.to_dict()},
                               event="deploy_error")
            return "failed"

    def _build_improvement_note(self, issue: Dict) -> str:
        """Build a markdown improvement note."""
        return (
            f"# Improvement Note\n\n"
            f"**Generated:** {datetime.utcnow().isoformat()}\n\n"
            f"**Issue Type:** {issue['type']}\n\n"
            f"**Description:** {issue['description']}\n\n"
            f"**Recommended Action:**\n"
            f"- Review recent failure logs\n"
            f"- Identify root cause\n"
            f"- Update error handling in affected agent\n"
        )

    def _write_audit(self, data: Dict, event: str = "cycle_summary") -> None:
        """Append event to audit log."""
        entry = {"event": event, "timestamp": datetime.utcnow().isoformat(), **data}
        with open(self.audit_log, "a") as f:
            f.write(json.dumps(entry) + "\n")
