# 🤖 Self-Improving AI Agent System

> An autonomous, production-grade AI agent that assists in software development, cybersecurity, and web building — while continuously improving its own codebase.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Author](https://img.shields.io/badge/Author-skytech45-orange)
![Version](https://img.shields.io/badge/Version-1.0.0-purple)

---

## ✨ Features

- 🧠 **Multi-Agent Architecture** — Coding, Web, and Security agents with intelligent routing
- 🔁 **Self-Improvement Loop** — Analyzes failures, generates improvements, validates, and deploys
- 🔐 **Security-First** — Sandbox execution, dangerous pattern blocking, no unsafe self-modification
- 📦 **Memory System** — Short-term context + long-term JSON persistence + failure logging
- ✅ **Validation Pipeline** — Syntax → Linting → Security scan → Sandbox execution
- 🐙 **GitHub Automation** — Auto-commits improvements with structured messages
- ⏰ **Scheduler** — Daily improvement cycles running in background
- 🐳 **Docker Ready** — Containerized with non-root user

---

## 📁 Project Structure

```
self-improving-ai-agent/
├── main.py                          # Entry point
├── core/
│   ├── engine.py                    # Central orchestrator
│   └── config.py                    # Config loader
├── agents/
│   ├── base_agent.py                # Abstract base
│   ├── coding_agent.py              # Python dev agent
│   ├── web_agent.py                 # FastAPI/Flask/HTML agent
│   └── security_agent.py            # Ethical security agent
├── memory/
│   └── memory_manager.py            # Short + long-term + logs
├── self_improvement/
│   └── improvement_engine.py        # Analyze → Generate → Deploy
├── validation/
│   └── validator.py                 # Multi-stage validation
├── github/
│   └── git_manager.py               # GitHub API automation
├── scheduler/
│   └── task_scheduler.py            # Background task runner
├── utils/
│   └── logger.py                    # Centralized logging
├── tests/
│   └── test_agents.py               # Unit tests
├── configs/
│   └── config.yaml                  # System configuration
├── ARCHITECTURE.md                  # System design docs
├── Dockerfile                       # Container deployment
└── requirements.txt
```

---

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/skytech45/self-improving-ai-agent.git
cd self-improving-ai-agent
pip install -r requirements.txt

# Set environment variables
export GITHUB_ACCESS_TOKEN=your_token
export OPENAI_API_KEY=your_key         # Optional
export GITHUB_REPO=skytech45/self-improving-ai-agent

# Run a task
python main.py run --task "write a python function to sort a list"

# Trigger improvement cycle
python main.py improve

# Start background scheduler (runs every 24h)
python main.py schedule --interval 24

# Check system status
python main.py status
```

---

## 🐳 Docker

```bash
docker build -t self-improving-ai-agent .
docker run \
  -e GITHUB_ACCESS_TOKEN=xxx \
  -e OPENAI_API_KEY=xxx \
  self-improving-ai-agent
```

---

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

---

## ⚙️ Configuration

Edit `configs/config.yaml` to tune:
- LLM model and temperature
- Improvement cycle interval
- Validation strictness
- GitHub auto-push settings

Or use environment variables:
```bash
export AIAGENT_LLM_MODEL=gpt-4o
export AIAGENT_IMPROVEMENT_CYCLE_INTERVAL_HOURS=12
```

---

## 🔐 Security Policy

- All code changes pass a **mandatory validation pipeline** before deployment
- Dangerous patterns (`eval`, `exec`, `os.system`, `DROP TABLE`) are **blocked**
- New code runs in an **isolated subprocess sandbox** with a hard timeout
- Secrets are managed via **environment variables only** — never committed
- The system runs as a **non-root user** inside Docker

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 👨‍💻 Author

**Sachin Kumar (skytech45)**  
Electronics Engineering Student | AI & Cybersecurity Enthusiast  
📍 Bihar, India | [GitHub](https://github.com/skytech45)

---

*Actively maintained as part of a developer portfolio.*
