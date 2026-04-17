"""
agents/builder_agent.py

Builder Agent — generates solutions for coding, web, and engineering tasks.
Produces structured AgentResult with confidence scoring.
"""

from __future__ import annotations

import ast
import re
from typing import Any, Dict, List

from agents.base_agent import BaseAgent, AgentResult


class BuilderAgent(BaseAgent):
    """
    Builder Agent: the primary solution generator.

    Responsibilities:
    - Write Python code (functions, classes, modules)
    - Scaffold web applications (FastAPI, Flask, HTML)
    - Generate implementation plans for complex tasks
    - Add type hints, docstrings, error handling

    Output is always structured as AgentResult with
    confidence score based on code quality heuristics.
    """

    KEYWORDS = [
        "write", "create", "build", "implement", "generate",
        "code", "function", "class", "script", "module", "scaffold",
        "develop", "design", "make", "construct",
    ]

    def __init__(self, memory=None, config: Dict[str, Any] = None):
        super().__init__("BuilderAgent", memory, config)

    def can_handle(self, task: str) -> bool:
        return any(kw in task.lower() for kw in self.KEYWORDS)

    def execute(self, task: str) -> AgentResult:
        """Generate a solution for the given task."""
        self.logger.info(f"Building solution for: {task[:70]}")
        intent  = self._classify_intent(task)
        code    = self._generate(intent, task)
        issues  = self._quality_check(code)
        confidence = self._score_confidence(code, issues)

        result = AgentResult(
            agent_name  = self.name,
            output      = code,
            confidence  = confidence,
            issues      = issues,
            passed      = confidence >= 0.5,
            metadata    = {"intent": intent},
        )
        self._store_context(task, result)
        return result

    def critique(self, result: AgentResult) -> AgentResult:
        """Review another agent's output for correctness."""
        issues = []
        if len(result.output) < 50:
            issues.append("Output too short — likely incomplete.")
        if "TODO" in result.output:
            issues.append("Contains unimplemented TODOs.")
        if "pass" in result.output and "def " in result.output:
            issues.append("Function stubs with bare pass detected.")
        valid, err = self._validate_syntax(result.output)
        if not valid:
            issues.append(f"Syntax error: {err}")
        return AgentResult(
            agent_name  = f"{self.name}:critique",
            output      = "\n".join(issues) if issues else "No issues found.",
            confidence  = 1.0 - (len(issues) * 0.15),
            issues      = issues,
            passed      = len(issues) == 0,
        )

    # ── Private ────────────────────────────────────────────────────

    def _classify_intent(self, task: str) -> str:
        t = task.lower()
        if any(k in t for k in ["fastapi", "flask", "api", "endpoint", "route"]): return "web_api"
        if any(k in t for k in ["html", "css", "frontend", "landing", "page"]): return "web_frontend"
        if any(k in t for k in ["class", "oop", "object"]): return "oop"
        if any(k in t for k in ["test", "unittest", "pytest"]): return "test"
        if any(k in t for k in ["cli", "argparse", "command"]): return "cli"
        return "function"

    def _generate(self, intent: str, task: str) -> str:
        name = self._extract_name(task)
        generators = {
            "function":    self._gen_function,
            "oop":         self._gen_class,
            "web_api":     self._gen_fastapi,
            "web_frontend":self._gen_html,
            "test":        self._gen_test,
            "cli":         self._gen_cli,
        }
        return generators.get(intent, self._gen_function)(name, task)

    def _gen_function(self, name: str, task: str) -> str:
        return f'''from typing import Any, Optional


def {name}(data: Any) -> Optional[Any]:
    """
    {task.strip()[:120]}

    Args:
        data: Input data

    Returns:
        Processed result or None on failure

    Raises:
        ValueError: If input is invalid
        RuntimeError: If processing fails
    """
    if data is None:
        raise ValueError(f"{{name}}: data must not be None")

    try:
        # TODO: Implement core logic
        result = data
        return result
    except Exception as exc:
        raise RuntimeError(f"{{name}} failed: {{exc}}") from exc


if __name__ == "__main__":
    print({name}("test"))
'''

    def _gen_class(self, name: str, task: str) -> str:
        cls = "".join(w.capitalize() for w in name.split("_"))
        return f'''from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging


@dataclass
class {cls}:
    """
    {task.strip()[:120]}

    Attributes:
        name:   Identifier
        config: Runtime configuration
    """
    name:   str
    config: Dict[str, Any] = field(default_factory=dict)
    _state: Dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.info(f"{{self.__class__.__name__}} initialized: {{self.name}}")

    def process(self, input_data: Any) -> Any:
        """Process input and return result."""
        raise NotImplementedError

    def validate(self) -> bool:
        """Validate internal state."""
        return bool(self.name)

    def to_dict(self) -> Dict[str, Any]:
        return {{"name": self.name, "config": self.config}}
'''

    def _gen_fastapi(self, name: str, task: str) -> str:
        return '''from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import uvicorn

app = FastAPI(title="AI-Generated API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                  allow_methods=["*"], allow_headers=["*"])

class ItemSchema(BaseModel):
    id:          Optional[int] = None
    name:        str           = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    active:      bool          = True

_db: List[ItemSchema] = []

@app.get("/health", tags=["System"])
def health(): return {"status": "ok"}

@app.get("/items", response_model=List[ItemSchema])
def list_items(): return _db

@app.post("/items", response_model=ItemSchema, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemSchema):
    item.id = len(_db) + 1
    _db.append(item)
    return item

@app.get("/items/{item_id}", response_model=ItemSchema)
def get_item(item_id: int):
    for i in _db:
        if i.id == item_id: return i
    raise HTTPException(status_code=404, detail="Not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

    def _gen_html(self, name: str, task: str) -> str:
        return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>skytech45 | AI Agent</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:"Segoe UI",sans-serif;background:#0a0a0f;color:#e0e0e0}
    header{background:#0d1b2a;padding:1.2rem 2rem;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1e3a5f}
    header h1{color:#00c8ff;font-size:1.4rem;letter-spacing:.05em}
    nav a{color:#90a4ae;margin-left:1.5rem;text-decoration:none;font-size:.9rem}
    nav a:hover{color:#00c8ff}
    .hero{text-align:center;padding:6rem 2rem;background:linear-gradient(135deg,#0d1b2a,#0a0a0f)}
    .hero h2{font-size:2.6rem;color:#00c8ff;margin-bottom:1rem;letter-spacing:-.02em}
    .hero p{color:#90a4ae;max-width:560px;margin:.8rem auto;line-height:1.7}
    .badge{display:inline-block;background:#1e3a5f;color:#00c8ff;padding:.3rem .8rem;border-radius:20px;font-size:.8rem;margin:.3rem}
    .btn{display:inline-block;margin-top:2rem;background:#00c8ff;color:#0a0a0f;padding:.9rem 2.2rem;border-radius:6px;font-weight:700;text-decoration:none;letter-spacing:.04em}
    .btn:hover{background:#00a8d8}
    footer{text-align:center;padding:2rem;color:#546e7a;font-size:.8rem;border-top:1px solid #1e3a5f}
  </style>
</head>
<body>
  <header>
    <h1>⚡ skytech45</h1>
    <nav><a href="#">Home</a><a href="#">Projects</a><a href="#">Docs</a><a href="#">Contact</a></nav>
  </header>
  <section class="hero">
    <h2>Self-Improving AI Agent</h2>
    <p>Autonomous software development, cybersecurity analysis, and continuous self-optimization powered by multi-agent intelligence.</p>
    <div>
      <span class="badge">Python 3.11</span><span class="badge">Multi-Agent</span>
      <span class="badge">Self-Improving</span><span class="badge">Security-First</span>
    </div>
    <a href="#" class="btn">Explore System →</a>
  </section>
  <footer>Built by skytech45 | Self-Improving AI Agent System v1.0</footer>
</body>
</html>
'''

    def _gen_test(self, name: str, task: str) -> str:
        return f'''import unittest
from unittest.mock import MagicMock, patch


class Test{name.replace("_","").capitalize()}(unittest.TestCase):

    def setUp(self):
        """Initialise fixtures before each test."""
        self.mock_config = {{"debug": True, "timeout": 5}}

    def test_happy_path(self):
        """Verify normal operation returns expected result."""
        self.assertTrue(True)  # Replace with real assertion

    def test_none_input_raises(self):
        """Verify None input raises ValueError."""
        with self.assertRaises((ValueError, TypeError)):
            pass  # Replace with actual call

    def test_empty_input(self):
        """Verify empty input is handled gracefully."""
        self.assertIsNotNone(None)  # Replace

    def test_timeout(self):
        """Verify operation respects timeout constraints."""
        import time
        start = time.time()
        # Replace with actual call
        self.assertLess(time.time() - start, self.mock_config["timeout"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''

    def _gen_cli(self, name: str, task: str) -> str:
        return f'''#!/usr/bin/env python3
"""CLI tool: {task[:80]}"""
import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def run(args: argparse.Namespace) -> int:
    """Main logic. Returns exit code."""
    logger.info(f"Running {name} with args={{vars(args)}}")
    # TODO: implement
    return 0

def main() -> None:
    parser = argparse.ArgumentParser(description="{task[:80]}")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--output",  "-o", default="-", help="Output file (- for stdout)")
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    sys.exit(run(args))

if __name__ == "__main__":
    main()
'''

    @staticmethod
    def _extract_name(task: str) -> str:
        words = re.findall(r"[a-zA-Z]+", task)
        stop  = {"write","create","build","make","a","an","the","for","that",
                 "which","python","function","class","script","generate","implement"}
        parts = [w.lower() for w in words if w.lower() not in stop]
        return "_".join(parts[:3]) or "solution"

    @staticmethod
    def _validate_syntax(code: str):
        import ast
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, str(e)

    def _quality_check(self, code: str) -> List[str]:
        issues = []
        if "TODO" in code:           issues.append("Contains unimplemented TODO.")
        if len(code.strip()) < 30:   issues.append("Output suspiciously short.")
        if "raise NotImplementedError" in code:
            issues.append("NotImplementedError present — stub only.")
        return issues

    def _score_confidence(self, code: str, issues: List[str]) -> float:
        base = 0.80
        valid, _ = self._validate_syntax(code)
        if not valid:     base -= 0.40
        base -= len(issues) * 0.08
        if len(code) > 200: base += 0.05
        if "def " in code:  base += 0.03
        if '"""' in code:   base += 0.03
        return round(max(0.0, min(1.0, base)), 3)
