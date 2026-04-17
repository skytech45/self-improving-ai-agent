"""
agents/consensus.py

Multi-Agent Consensus Engine.
Aggregates results from Builder, Critic, Security, Optimizer.
Uses weighted scoring with security veto power.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
from agents.base_agent import AgentResult
from utils.logger import get_logger


AGENT_WEIGHTS: Dict[str, float] = {
    "BuilderAgent":   0.35,
    "CriticAgent":    0.30,
    "SecurityAgent":  0.25,
    "OptimizerAgent": 0.10,
}


@dataclass
class ConsensusResult:
    """Final multi-agent consensus verdict."""
    final_output:    str
    consensus_score: float
    approved:        bool
    votes:           Dict[str, bool]  = field(default_factory=dict)
    all_issues:      List[str]        = field(default_factory=list)
    all_suggestions: List[str]        = field(default_factory=list)
    agent_scores:    Dict[str, float] = field(default_factory=dict)
    blocking_issues: List[str]        = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved":        self.approved,
            "consensus_score": round(self.consensus_score, 3),
            "votes":           self.votes,
            "issues_count":    len(self.all_issues),
            "blocking_count":  len(self.blocking_issues),
        }


class ConsensusEngine:
    """
    Multi-agent voting and consensus system.

    Scoring model:
    - Builder Agent:   35% weight (primary output)
    - Critic Agent:    30% weight (quality gatekeeper)
    - Security Agent:  25% weight (security veto power)
    - Optimizer Agent: 10% weight (performance advisory)

    Approval criteria:
    - Weighted score >= threshold (default 0.65)
    - Zero blocking security issues
    - Builder result marked as passed
    """

    def __init__(self, threshold: float = 0.65, config: Dict[str, Any] = None):
        self.threshold = threshold
        self.config    = config or {}
        self.logger    = get_logger("ConsensusEngine")

    def evaluate(
        self,
        builder_result: AgentResult,
        critiques:      List[AgentResult],
    ) -> ConsensusResult:
        """
        Aggregate all agent results into a consensus verdict.

        Args:
            builder_result: Primary output from BuilderAgent
            critiques:      Critique AgentResults from Critic/Security/Optimizer

        Returns:
            ConsensusResult with approval decision
        """
        all_issues:      List[str] = list(builder_result.issues)
        all_suggestions: List[str] = list(builder_result.suggestions)
        blocking:        List[str] = []
        votes:  Dict[str, bool]  = {builder_result.agent_name: builder_result.passed}
        scores: Dict[str, float] = {builder_result.agent_name: builder_result.score()}

        for cr in critiques:
            votes[cr.agent_name]  = cr.passed
            scores[cr.agent_name] = cr.score()
            all_issues.extend(cr.issues)
            all_suggestions.extend(cr.suggestions)
            # Security issues with BLOCKED or credential keyword are veto-blocking
            if "SecurityAgent" in cr.agent_name:
                blocking.extend([
                    i for i in cr.issues
                    if "BLOCKED" in i.upper() or "HARDCODED" in i.upper()
                    or "INJECTION" in i.upper()
                ])

        weighted = self._weighted_score(scores)
        approved = (
            weighted >= self.threshold
            and len(blocking) == 0
            and builder_result.passed
        )

        self.logger.info(
            f"Consensus: score={weighted:.3f} approved={approved} "
            f"blocking={len(blocking)} total_issues={len(all_issues)}"
        )

        return ConsensusResult(
            final_output    = builder_result.output,
            consensus_score = weighted,
            approved        = approved,
            votes           = votes,
            all_issues      = list(set(all_issues)),
            all_suggestions = list(set(all_suggestions)),
            agent_scores    = scores,
            blocking_issues = blocking,
        )

    def _weighted_score(self, scores: Dict[str, float]) -> float:
        total_w, total_s = 0.0, 0.0
        for agent, score in scores.items():
            base = agent.split(":")[0]
            w = AGENT_WEIGHTS.get(base, 0.10)
            total_s += score * w
            total_w += w
        return round(total_s / total_w, 4) if total_w else 0.0

    def format_report(self, result: ConsensusResult) -> str:
        """Format a human-readable consensus report."""
        status = "APPROVED" if result.approved else "REJECTED"
        lines = [
            "=" * 55,
            "  MULTI-AGENT CONSENSUS REPORT",
            "=" * 55,
            f"  Status  : {status}",
            f"  Score   : {result.consensus_score:.3f} (threshold: {self.threshold})",
            "-" * 55,
            "  Agent Votes:",
        ]
        for agent, voted in result.votes.items():
            score = result.agent_scores.get(agent, 0.0)
            mark  = "PASS" if voted else "FAIL"
            lines.append(f"    [{mark}] {agent:<35} {score:.3f}")
        if result.blocking_issues:
            lines.append("\n  BLOCKING ISSUES (veto):")
            for b in result.blocking_issues:
                lines.append(f"    {b}")
        if result.all_issues:
            lines.append(f"\n  All Issues ({len(result.all_issues)}):")
            for i in result.all_issues[:5]:
                lines.append(f"    - {i}")
        lines.append("=" * 55)
        return "\n".join(lines)
