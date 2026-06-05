FROM python:3.12-slim

LABEL org.opencontainers.image.title="AgentRL"
LABEL org.opencontainers.image.description="Local-first Harness Operating System for defining, evaluating, evolving, versioning, and deploying agent harnesses."
LABEL org.opencontainers.image.source="https://github.com/junaidahmed361/agentrl"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir .

WORKDIR /workspace
ENTRYPOINT ["agentrl"]
CMD ["--help"]
