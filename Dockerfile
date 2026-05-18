# ─── Build Stage ───────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml setup.py requirements.txt ./
COPY openmind/ openmind/
RUN pip install --no-cache-dir --prefix=/install .

# ─── Runtime Stage ────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

COPY --from=builder /install /usr/local
COPY openmind/ openmind/
COPY bot/ bot/
COPY landing/ landing/

# Config directory
RUN mkdir -p /root/.openmind

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default: run CLI
ENTRYPOINT ["openmind"]
CMD ["chat", "--provider", "groq"]
