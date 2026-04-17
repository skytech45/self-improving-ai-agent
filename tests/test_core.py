import unittest
from unittest.mock import MagicMock, patch
from core.engine import AgentEngine

class TestAgentEngine(unittest.TestCase):
    def setUp(self):
        # Mock configuration
        self.config = {
            "memory": {},
            "github": {},
            "validation": {},
            "improvement": {},
            "coding": {},
            "web": {},
            "security": {}
        }
        # Initialize engine with dry_run to avoid actual API calls
        self.engine = AgentEngine(config=self.config, dry_run=True)

    def test_classify_task_coding(self):
        task = "Write a python script to parse logs"
        self.assertEqual(self.engine.classify_task(task), "coding")

    def test_classify_task_web(self):
        task = "Create a FastAPI backend for a todo app"
        self.assertEqual(self.engine.classify_task(task), "web")

    def test_classify_task_security(self):
        task = "Scan this website for vulnerabilities"
        self.assertEqual(self.engine.classify_task(task), "security")

    @patch('agents.coding_agent.CodingAgent.execute')
    def test_run_task_success(self, mock_execute):
        mock_execute.return_value = "Task completed successfully"
        result = self.engine.run_task("write code")
        self.assertEqual(result, "Task completed successfully")

    @patch('agents.coding_agent.CodingAgent.execute')
    def test_run_task_failure(self, mock_execute):
        mock_execute.side_effect = Exception("Execution error")
        result = self.engine.run_task("write code")
        self.assertTrue(result.startswith("[ERROR]"))

if __name__ == '__main__':
    unittest.main()
