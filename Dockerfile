FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -e ".[full]"

# Copy application
COPY exort/ exort/
COPY tests/ tests/

# Create exort home
RUN mkdir -p /root/.exort/skills /root/.exort/logs

# Default: run the Telegram bot (override with: docker run ... exort shell)
ENTRYPOINT ["exort"]
CMD ["bot"]
