FROM python:3.12-slim

WORKDIR /app

# Install dependencies (non-editable for Docker)
COPY pyproject.toml requirements.txt ./
COPY exort/ exort/
COPY tests/ tests/
RUN pip install --no-cache-dir ".[full]"

# Create exort home
RUN mkdir -p /root/.exort/skills /root/.exort/logs

# Health check port (keeps Render free tier alive)
EXPOSE 8080

# Default: run the Telegram bot
ENTRYPOINT ["exort"]
CMD ["bot"]
