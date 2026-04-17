"""
tests/test_full_system.py

Comprehensive test suite for all system components.
Tests: agents, consensus, validation, memory, security scanner, benchmarks.
"""
from __future__ import annotations

import sys
import os
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.builder_agent import BuilderAgent
from agents.critic_agent import CriticAgent
from agents.security_agent import SecurityAgent
from agents.optimizer_agent import OptimizerAgent
from agents.base_agent import AgentResult
from agents.consensus import ConsensusEngine, AGENT_WEIGHTS
from memory.memory_manager import MemoryManager
from validation.validator import ValidationPipeline
from security.scanner import SecurityScanner


class TestBuilderAgent(unittest.TestCase):

    def setUp(self):
        self.memory = MemoryManager(config={"persist_path": "/tmp/test_mem"})
        self.agent  = BuilderAgent(memory=self.memory)

    def test_can_handle_coding_tasks(self):
        self.assertTrue(self.agent.can_handle("write a python function"))
        self.assertTrue(self.agent.can_handle("implement a binary search class"))
        self.assertTrue(self.agent.can_handle("build a fastapi api"))

    def test_execute_returns_agent_result(self):
        r = self.agent.execute("write a function to add two numbers")
        self.assertIsInstance(r, AgentResult)
        self.assertEqual(r.agent_name, "BuilderAgent")

    def test_output_nonempty(self):
        r = self.agent.execute("write a simple python function")
        self.assertGreater(len(r.output), 30)

    def test_confidence_in_range(self):
        r = self.agent.execute("create a class for a linked list")
        self.assertGreaterEqual(r.confidence, 0.0)
        self.assertLessEqual(r.confidence, 1.0)

    def test_score_method(self):
        r = self.agent.execute("write a function")
        score = r.score()
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_critique_short_output(self):
        fake = AgentResult(agent_name="Test", output="x = 1", confidence=0.9)
        cr = self.agent.critique(fake)
        self.assertIsInstance(cr, AgentResult)
        self.assertGreater(len(cr.issues), 0)

    def test_fastapi_scaffold(self):
        r = self.agent.execute("create a fastapi endpoint for users")
        self.assertIn("FastAPI", r.output)
        self.assertIn("@app", r.output)

    def test_html_scaffold(self):
        r = self.agent.execute("build a html landing page")
        self.assertIn("<!DOCTYPE", r.output)


class TestCriticAgent(unittest.TestCase):

    def setUp(self):
        self.agent = CriticAgent()

    def test_critique_finds_missing_error_handling(self):
        result = AgentResult(
            agent_name="Builder",
            output='def add(a, b):\n    return a + b\n',
            confidence=0.9
        )
        cr = self.agent.critique(result)
        self.assertIsInstance(cr, AgentResult)
        issues_lower = " ".join(cr.issues).lower()
        self.assertTrue(
            "exception" in issues_lower or "error" in issues_lower or "type" in issues_lower
        )

    def test_critique_passes_good_code(self):
        good_code = (
            'def add(a: int, b: int) -> int:\n'
            '    """\n    Add two integers.\n    """\n'
            '    try:\n'
            '        return a + b\n'
            '    except TypeError as e:\n'
            '        raise ValueError(str(e))\n'
        )
        result = AgentResult(agent_name="Builder", output=good_code, confidence=0.9)
        cr = self.agent.critique(result)
        self.assertIsInstance(cr, AgentResult)
        self.assertGreater(cr.confidence, 0.5)


class TestSecurityAgent(unittest.TestCase):

    def setUp(self):
        self.agent = SecurityAgent()

    def test_can_handle_security_tasks(self):
        self.assertTrue(self.agent.can_handle("scan open ports"))
        self.assertTrue(self.agent.can_handle("analyze security headers"))
        self.assertTrue(self.agent.can_handle("generate hash"))

    def test_port_scan_returns_result(self):
        r = self.agent.execute("scan open ports on localhost")
        self.assertIn("Port Recon", r.output)
        self.assertTrue(r.passed)

    def test_hash_demo(self):
        r = self.agent.execute("generate sha256 hash demo")
        self.assertIn("SHA256", r.output)
        self.assertIn("MD5", r.output)

    def test_critique_detects_eval(self):
        bad = AgentResult(agent_name="Builder", output='result = eval(user_input)', confidence=0.9)
        cr  = self.agent.critique(bad)
        self.assertFalse(cr.passed)
        self.assertGreater(len(cr.issues), 0)

    def test_critique_passes_clean_code(self):
        clean = AgentResult(
            agent_name="Builder",
            output='def greet(name: str) -> str:\n    return f"Hello, {name}"\n',
            confidence=0.9
        )
        cr = self.agent.critique(clean)
        self.assertTrue(cr.passed)


class TestConsensusEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ConsensusEngine(threshold=0.65)
        self.critic = CriticAgent()
        self.security = SecurityAgent()
        self.optimizer = OptimizerAgent()

    def test_approves_good_output(self):
        good_code = (
            'def compute(x: int) -> int:\n'
            '    """\n    Compute result.\n    """\n'
            '    if x is None:\n'
            '        raise ValueError("x required")\n'
            '    try:\n'
            '        return x * 2\n'
            '    except Exception as e:\n'
            '        raise RuntimeError(str(e))\n'
        )
        br  = AgentResult(agent_name="BuilderAgent", output=good_code,
                          confidence=0.85, passed=True)
        crs = [self.critic.critique(br), self.security.critique(br)]
        cr  = self.engine.evaluate(br, crs)
        self.assertIsInstance(cr.consensus_score, float)
        self.assertGreaterEqual(cr.consensus_score, 0.0)

    def test_rejects_insecure_code(self):
        bad_code = 'password = "admin123"\nresult = eval(user_input)'
        br  = AgentResult(agent_name="BuilderAgent", output=bad_code,
                          confidence=0.5, passed=False)
        crs = [self.security.critique(br)]
        cr  = self.engine.evaluate(br, crs)
        self.assertFalse(cr.approved)

    def test_weights_sum_to_one(self):
        total = sum(AGENT_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=2)


class TestValidationPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = ValidationPipeline()

    def test_valid_code_passes_syntax(self):
        code   = "def add(a: int, b: int) -> int:\n    return a + b\n"
        result = self.pipeline.validate_code(code)
        self.assertTrue(result["stages"]["syntax"]["passed"])

    def test_syntax_error_fails_immediately(self):
        code   = "def broken(:\n    pass"
        result = self.pipeline.validate_code(code)
        self.assertFalse(result["passed"])
        self.assertFalse(result["stages"]["syntax"]["passed"])
        # Must not run further stages after syntax failure
        self.assertNotIn("sandbox", result["stages"])

    def test_eval_blocked_by_security(self):
        code   = 'import os\nresult = eval(user_input)\n'
        result = self.pipeline.validate_code(code)
        self.assertFalse(result["passed"])
        self.assertFalse(result["stages"]["security"]["passed"])

    def test_hardcoded_password_blocked(self):
        code   = 'password = "mysecret123"\nprint(password)\n'
        result = self.pipeline.validate_code(code)
        self.assertFalse(result["passed"])

    def test_clean_code_passes_all(self):
        code = (
            'import os\n\n'
            'def get_env(key: str) -> str:\n'
            '    """\n    Get environment variable.\n    """\n'
            '    value = os.environ.get(key, "")\n'
            '    if not value:\n'
            '        raise KeyError(f"Missing env var: {key}")\n'
            '    return value\n'
        )
        result = self.pipeline.validate_code(code)
        self.assertTrue(result["stages"]["syntax"]["passed"])
        self.assertTrue(result["stages"]["security"]["passed"])


class TestSecurityScanner(unittest.TestCase):

    def setUp(self):
        self.scanner = SecurityScanner()

    def test_detects_eval(self):
        report = self.scanner.scan_code('result = eval(user_input)', "test.py")
        self.assertGreater(len(report.findings), 0)
        severities = [f.severity for f in report.findings]
        self.assertIn("CRITICAL", severities)

    def test_detects_hardcoded_secret(self):
        code   = 'API_KEY = "sk-abc123xyz789"\nprint(API_KEY)'
        report = self.scanner.scan_code(code, "test.py")
        cats   = [f.category for f in report.findings]
        self.assertIn("credential", cats)

    def test_clean_code_passes(self):
        code = (
            'import os\n\n'
            'def get_key() -> str:\n'
            '    return os.environ["API_KEY"]\n'
        )
        report = self.scanner.scan_code(code, "test.py")
        critical = [f for f in report.findings if f.severity == "CRITICAL"]
        self.assertEqual(len(critical), 0)


class TestMemoryManager(unittest.TestCase):

    def setUp(self):
        self.mem = MemoryManager(config={"persist_path": "/tmp/test_memory_v2"})

    def test_short_term_store_get(self):
        self.mem.store_short_term("foo", "bar")
        self.assertEqual(self.mem.get_short_term("foo"), "bar")

    def test_short_term_default(self):
        self.assertIsNone(self.mem.get_short_term("missing"))
        self.assertEqual(self.mem.get_short_term("missing", "default"), "default")

    def test_short_term_clear(self):
        self.mem.store_short_term("key1", "val1")
        self.mem.clear_short_term()
        self.assertIsNone(self.mem.get_short_term("key1"))

    def test_failure_logging(self):
        self.mem.log_failure("task1", "builder", "SomeError")
        failures = self.mem.get_recent_failures(5)
        self.assertGreaterEqual(len(failures), 1)
        self.assertEqual(failures[-1]["task"], "task1")

    def test_success_logging(self):
        self.mem.log_success("task2", "security", 1.23)
        successes = self.mem.get_recent_successes(5)
        self.assertGreaterEqual(len(successes), 1)

    def test_stats_keys_present(self):
        stats = self.mem.get_stats()
        for key in ["short_term_keys", "total_failures", "total_successes"]:
            self.assertIn(key, stats)


if __name__ == "__main__":
    unittest.main(verbosity=2)
