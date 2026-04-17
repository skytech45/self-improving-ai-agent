# 🤖 Self-Improving AI Agent System

> An autonomous, production-grade AI agent system designed to assist in software development, cybersecurity, and web building, with the unique capability to continuously improve its own performance and safely update its own codebase.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Author](https://img.shields.io/badge/Author-skytech45-orange)
![Version](https://img.shields.io/badge/Version-1.0.0-purple)

---

## 🎯 Core Objective

The **Self-Improving AI Agent System** is built to be a truly autonomous partner for developers and security researchers. It doesn't just execute tasks; it learns from its own execution history, identifies failures or inefficiencies, and generates verified code updates to improve its own internal logic and toolset.

## ✨ Key Features

- 🧠 **Multi-Agent Orchestration**: Specialized agents for **Coding**, **Web Development**, and **Cybersecurity** with intelligent task routing.
- 🔁 **Self-Improvement Loop**: A dedicated engine that analyzes execution logs, identifies bottlenecks or errors, and proposes codebase enhancements.
- 🔐 **Security-First Architecture**: Mandatory validation pipeline including static analysis, dangerous pattern blocking, and sandboxed execution.
- 📦 **Hybrid Memory System**: Combines short-term task context with long-term persistent storage and structured failure logging.
- ✅ **Automated Validation**: Multi-stage verification (Syntax → Linting → Security → Sandbox) ensures only safe, working code is deployed.
- 🐙 **GitHub Integration**: Full lifecycle automation—from identifying an improvement to committing and pushing the verified update.
- ⏰ **Autonomous Scheduler**: Built-in background runner for periodic self-analysis and improvement cycles.

---

## 🏗️ System Architecture

The system follows a modular, decoupled architecture to ensure reliability and extensibility:

1.  **Core Engine**: The central brain that coordinates task planning, agent routing, and memory access.
2.  **Skill Agents**: Specialized modules (Coding, Web, Security) that implement domain-specific logic and tools.
3.  **Memory Manager**: Handles state persistence, context retrieval, and historical performance logging.
4.  **Self-Improvement Engine**: The meta-cognitive layer that performs "introspection" on the system's performance.
5.  **Validation Pipeline**: The safety gatekeeper that runs all candidate updates through a battery of tests and security checks.
6.  **Git Manager**: Interfaces with the GitHub API to maintain version history and deploy improvements.

---

## 📂 Project Structure

```text
self-improving-ai-agent/
├── main.py                          # Entry point and CLI interface
├── core/
│   ├── engine.py                    # Central orchestration logic
│   └── config.py                    # Configuration management
├── agents/
│   ├── base_agent.py                # Abstract base for all agents
│   ├── coding_agent.py              # Python development & debugging
│   ├── web_agent.py                 # Web scaffolding & API development
│   └── security_agent.py            # Vulnerability scanning & analysis
├── memory/
│   └── memory_manager.py            # Persistence and context management
├── self_improvement/
│   └── improvement_engine.py        # Introspection and code generation
├── validation/
│   └── validator.py                 # Safety and correctness verification
├── github/
│   └── git_manager.py               # Git/GitHub automation
├── scheduler/
│   └── task_scheduler.py            # Background cycle management
├── utils/
│   └── logger.py                    # Structured system logging
├── tests/
│   └── test_agents.py               # Comprehensive test suite
├── configs/
│   └── config.yaml                  # System-wide settings
├── Dockerfile                       # Containerized deployment
└── requirements.txt                 # Project dependencies
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- A GitHub Access Token (for automation features)
- OpenAI API Key (optional, for LLM-powered features)

### Installation
```bash
# Clone the repository
git clone https://github.com/skytech45/self-improving-ai-agent.git
cd self-improving-ai-agent

# Install dependencies
pip install -r requirements.txt
```

### Configuration
Set up your environment variables:
```bash
export GITHUB_ACCESS_TOKEN="your_token_here"
export OPENAI_API_KEY="your_openai_key"
export GITHUB_REPO="skytech45/self-improving-ai-agent"
```

### Usage
```bash
# Execute a specific task
python main.py run --task "Implement a secure password hashing function in Python"

# Manually trigger a self-improvement cycle
python main.py improve

# Start the background scheduler (runs improvement cycle every 24 hours)
python main.py schedule --interval 24

# View current system statistics and status
python main.py status
```

---

## 🔐 Security & Safety Policy

Safety is the paramount constraint of this system. The following measures are strictly enforced:
- **No Direct Execution**: No self-generated code is ever executed directly on the host system without validation.
- **Sandbox Isolation**: All candidate updates and generated scripts run in a restricted subprocess sandbox.
- **Pattern Blocking**: A security scanner blocks dangerous keywords and functions (e.g., `eval`, `exec`, `os.system`).
- **Atomic Updates**: Improvements are applied as atomic Git commits, allowing for instant rollback if issues are detected post-deployment.
- **Non-Root Operation**: The system is designed to run with minimal privileges, especially within containerized environments.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Sachin Kumar (skytech45)**  
Electronics Engineering Student | AI & Cybersecurity Enthusiast  
📍 Bihar, India | [GitHub](https://github.com/skytech45)

---
*Developed as a demonstration of autonomous, self-evolving software systems.*
