"""
tests/test_agents.py
Unit tests for all skill agents and core components.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.coding_agent import CodingAgent
from agents.security_agent import SecurityAgent
from agents.web_agent import WebAgent
from memory.memory_manager import MemoryManager
from validation.validator import ValidationPipeline


class TestCodingAgent(unittest.TestCase):

    def setUp(self):
        self.memory = MemoryManager()
        self.agent  = CodingAgent(memory=self.memory)

    def test_can_handle_coding_task(self):
        self.assertTrue(self.agent.can_handle("write a python function"))
        self.assertTrue(self.agent.can_handle("debug this script"))
        self.assertTrue(self.agent.can_handle("refactor my code"))

    def test_cannot_handle_non_coding_task(self):
        self.assertFalse(self.agent.can_handle("scan open ports"))

    def test_execute_returns_string(self):
        result = self.agent.execute("write a function that adds two numbers")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10)

    def test_validate_syntax_valid_code(self):
        code = "def hello():\n    return 'world'"
        valid, err = CodingAgent.validate_syntax(code)
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_validate_syntax_invalid_code(self):
        code = "def broken(:\n    pass"
        valid, err = CodingAgent.validate_syntax(code)
        self.assertFalse(valid)
        self.assertIsNotNone(err)

    def test_sandbox_execution(self):
        code = "print('sandbox test')"
        result = self.agent.run_in_sandbox(code, timeout=5)
        self.assertTrue(result["success"])
        self.assertIn("sandbox test", result["stdout"])


class TestSecurityAgent(unittest.TestCase):

    def setUp(self):
        self.agent = SecurityAgent()

    def test_can_handle_security_task(self):
        self.assertTrue(self.agent.can_handle("scan ports on localhost"))
        self.assertTrue(self.agent.can_handle("analyze security headers"))
        self.assertTrue(self.agent.can_handle("generate hash for file"))

    def test_port_scan_returns_report(self):
        result = self.agent.execute("scan open ports on localhost")
        self.assertIsInstance(result, str)
        self.assertIn("Port Scan", result)

    def test_hash_tool_returns_hashes(self):
        result = self.agent.execute("generate a hash")
        self.assertIn("SHA256", result)
        self.assertIn("MD5", result)


class TestWebAgent(unittest.TestCase):

    def setUp(self):
        self.agent = WebAgent()

    def test_can_handle_web_task(self):
        self.assertTrue(self.agent.can_handle("build a fastapi app"))
        self.assertTrue(self.agent.can_handle("create html landing page"))

    def test_fastapi_scaffold_contains_expected(self):
        result = self.agent.execute("build a fastapi api")
        self.assertIn("FastAPI", result)
        self.assertIn("@app.get", result)

    def test_html_scaffold_is_valid(self):
        result = self.agent.execute("create html frontend page")
        self.assertIn("<!DOCTYPE html>", result)
        self.assertIn("<body>", result)


class TestMemoryManager(unittest.TestCase):

    def setUp(self):
        self.memory = MemoryManager(config={"persist_path": "/tmp/test_memory_store"})

    def test_short_term_store_and_get(self):
        self.memory.store_short_term("key1", "value1")
        self.assertEqual(self.memory.get_short_term("key1"), "value1")

    def test_short_term_default(self):
        self.assertIsNone(self.memory.get_short_term("nonexistent"))
        self.assertEqual(self.memory.get_short_term("nonexistent", "default"), "default")

    def test_failure_logging(self):
        self.memory.log_failure("test task", "coding", "Some error")
        failures = self.memory.get_recent_failures(5)
        self.assertGreaterEqual(len(failures), 1)

    def test_success_logging(self):
        self.memory.log_success("test task", "coding")
        successes = self.memory.get_recent_successes(5)
        self.assertGreaterEqual(len(successes), 1)


class TestValidationPipeline(unittest.TestCase):

    def setUp(self):
        self.validator = ValidationPipeline()

    def test_valid_code_passes(self):
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        result = self.validator.validate_code(code)
        self.assertTrue(result["stages"]["syntax"]["passed"])

    def test_invalid_syntax_fails(self):
        code = "def broken(:\n    pass"
        result = self.validator.validate_code(code)
        self.assertFalse(result["passed"])

    def test_dangerous_code_blocked(self):
        code = "import os\nos.system('ls')"
        result = self.validator.validate_code(code)
        self.assertFalse(result["passed"])
        self.assertTrue(any("BLOCKED" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
