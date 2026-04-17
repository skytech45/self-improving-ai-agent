# Self-Improving AI Agent — Dockerfile
FROM python:3.11-slim
LABEL maintainer="skytech45"
LABEL description="Self-Improving AI Agent System"
LABEL version="1.0.0"
RUN groupadd -r aiagent && useradd -r -g aiagent aiagent
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git curl && apt-get clean
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chown -R aiagent:aiagent /app
USER aiagent
RUN mkdir -p logs memory/store self_improvement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV AIAGENT_SECURITY_SANDBOX_MODE=true
CMD ["python", "main.py", "schedule", "--interval", "24"]
