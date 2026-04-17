# 🤖 Self-Improving AI Agent System

> A production-grade, research-level autonomous AI agent platform for software engineering, web development, and cybersecurity — with controlled self-improvement, multi-agent consensus, and full GitHub automation.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![Version](https://img.shields.io/badge/Version-2.0.0-purple)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Production--Grade-brightgreen)
![Author](https://img.shields.io/badge/Author-skytech45-orange)

---

## ⚡ What This Is

This is **not a chatbot wrapper**. It is a modular, security-first autonomous engineering platform with:

- Multi-agent internal debate (Builder → Critic → Security → Optimizer → Consensus)
- A mandatory multi-stage validation pipeline before any code touches the repo
- Branch-based self-improvement with PR creation and auto-merge after benchmark pass
- Regression detection to prevent deploying performance degradations
- Formal benchmark suite with 12 test cases across coding, web, and security domains
- Full audit log of every decision, deployment, and rejection

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    main.py  (CLI entry point)                    │
│         run | debate | improve | benchmark | scan | status       │
└────────────────────────┬────────────────────────────────────────┘
                         │
             ┌───────────▼───────────┐
             │     Orchestrator       │  orchestration/
             │  Sanitize → Plan       │
             │  → Dispatch → Aggregate│
             └──┬──┬──┬──────────────┘
    ┌───────────┘  │  └──────────────┐
    ▼              ▼                 ▼
┌──────────┐ ┌──────────┐ ┌──────────────────┐
│ Builder  │ │ Security │ │  Multi-Agent      │
│  Agent   │ │  Agent   │ │  Debate Pipeline  │
└──────────┘ └──────────┘ │  Builder+Critic   │
                          │  +Security+Optim  │
                          │  → ConsensusEngine│
                          └──────────────────┘
                         │
          ┌──────────────▼──────────────┐
          │  MemoryManager (4 layers)    │  memory/
          │  Short | Long | Episodic     │
          │  | Failure+Corrections       │
          └──────────────┬──────────────┘
                         │
          ┌──────────────▼──────────────┐
          │  ImprovementEngine           │  self_improvement/
          │  Analyze → Generate          │
          │  → Validate → Benchmark      │
          │  → Branch → PR → Auto-Merge  │
          └──────────────┬──────────────┘
                         │
          ┌──────────────▼──────────────┐
          │  ValidationPipeline          │  validation/
          │  Syntax → Security → Lint    │
          │  → Sandbox → Type-Check      │
          └──────────────┬──────────────┘
                         │
          ┌──────────────▼──────────────┐
          │  BenchmarkRunner             │  benchmarks/
          │  12 cases: coding+web+sec    │
          │  Regression detection        │
          └──────────────┬──────────────┘
                         │
          ┌──────────────▼──────────────┐
          │  GitManager                  │  github/
          │  Branch → Commit → PR        │
          │  Auto-merge | Rollback       │
          └─────────────────────────────┘
```

---

## 📁 Project Structure

```
self-improving-ai-agent/
├── main.py                          # Entry point — 7 CLI modes
├── orchestration/
│   ├── orchestrator.py              # Central task orchestrator
│   ├── task_planner.py              # Task decomposition
│   └── tool_controller.py           # Tool dispatch registry
├── agents/
│   ├── base_agent.py                # Abstract base (AgentResult)
│   ├── builder_agent.py             # Primary solution generator
│   ├── critic_agent.py              # Adversarial code reviewer
│   ├── security_agent.py            # Ethical security analyst
│   ├── optimizer_agent.py           # Performance analyst
│   └── consensus.py                 # Weighted voting engine
├── memory/
│   └── memory_manager.py            # 4-layer hybrid memory
├── validation/
│   └── validator.py                 # Multi-stage validation pipeline
├── security/
│   └── scanner.py                   # SAST — OWASP-based static scan
├── evaluation/
│   └── evaluation_engine.py         # Metrics + regression detection
├── self_improvement/
│   └── improvement_engine.py        # Controlled improvement cycle
├── github/
│   └── git_manager.py               # Branch + PR + merge + rollback
├── benchmarks/
│   └── benchmark_suite.py           # 12-case formal benchmark suite
├── scheduler/
│   └── task_scheduler.py            # Background daemon scheduler
├── tools/
│   └── file_tool.py                 # Safe file system interface
├── utils/
│   └── logger.py                    # Centralized logging
├── tests/
│   └── test_full_system.py          # 30+ unit tests
├── configs/
│   └── config.yaml                  # Full system configuration
├── ARCHITECTURE.md                  # System design documentation
└── Dockerfile                       # Non-root containerized deployment
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/skytech45/self-improving-ai-agent.git
cd self-improving-ai-agent
pip install -r requirements.txt

export GITHUB_ACCESS_TOKEN=your_token
export GITHUB_REPO=skytech45/self-improving-ai-agent

# Run a coding task
python main.py run --task "write a binary search function in Python"

# Multi-agent debate (Builder+Critic+Security+Optimizer)
python main.py debate --task "design a rate limiter system"

# Security scan the codebase
python main.py scan --target agents/

# Run the benchmark suite
python main.py benchmark

# Validate a Python file
python main.py validate --file agents/builder_agent.py

# Trigger self-improvement cycle (dry-run)
python main.py improve --dry-run

# Show system status
python main.py status
```

---

## 🔁 Self-Improvement Loop

```
1. COLLECT LOGS (failures, latency, repeated errors)
2. ANALYZE    → identify failure clusters and bottlenecks
3. GENERATE   → create improvement candidates
4. VALIDATE   → syntax + security + sandbox (MANDATORY)
5. BENCHMARK  → run 12-case suite, check for regression
6. If PASS:
     create branch → commit → open PR → auto-merge
7. If FAIL:
     log to failure memory → DO NOT DEPLOY → store correction
```

**Improvement only triggers when:**
> `performance_gain > 0.02 AND no_regression_detected`

---

## 🧠 Multi-Agent Debate

```
Task Input
    │
    ▼
BuilderAgent    → generates solution (weight: 35%)
    │
    ├─→ CriticAgent     → adversarial review (weight: 30%)
    ├─→ SecurityAgent   → security analysis  (weight: 25%)
    └─→ OptimizerAgent  → performance review (weight: 10%)
                │
                ▼
         ConsensusEngine
         ┌─ weighted score >= 0.65?
         ├─ zero BLOCKING security issues?
         └─ builder.passed = True?
              │
         APPROVED / REJECTED
```

---

## 🔐 Security Model

| Layer | Control |
|-------|---------|
| Execution | Subprocess sandbox with hard timeout |
| SAST | 20+ OWASP-based static patterns |
| Secrets | Environment variables only — never committed |
| Auth | Token-scoped GitHub API |
| Injection | Input sanitization before all LLM routing |
| Blocking | CRITICAL/HIGH findings veto any deployment |

---

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
# or
python tests/test_full_system.py
```

30+ test cases covering: agents, consensus, validation, memory, scanner.

---

## 🐳 Docker

```bash
docker build -t self-improving-ai-agent .
docker run \
  -e GITHUB_ACCESS_TOKEN=xxx \
  -e GITHUB_REPO=skytech45/self-improving-ai-agent \
  self-improving-ai-agent
```

---

## 📊 Benchmark Suite

12 formal test cases across 3 categories:
- **Coding** (5): binary search, stack, CLI tool, email validator, retry decorator
- **Web** (3): FastAPI endpoint, Flask API, HTML landing page
- **Security** (4): port scan, header audit, hash demo, injection prevention

Score = `success_rate * 0.70 + latency_score * 0.30`

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 👨‍💻 Author

**Sachin Kumar (skytech45)**
Electronics Engineering Student | AI & Cybersecurity Enthusiast
📍 Bihar, India | [GitHub](https://github.com/skytech45)

---

*Production-grade. Research-level. Actively maintained.*
