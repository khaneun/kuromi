# ── Stage 1: dependency installer ──────────────────────────────────────────
# This layer is cached unless pyproject.toml changes.
FROM python:3.11-slim AS deps

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
# Install only runtime dependencies (not the editable package itself) so the
# layer is cached independently from source code changes.
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir \
      "httpx>=0.27" \
      "websockets>=12" \
      "pyjwt>=2.8" \
      "pydantic>=2.6" \
      "pydantic-settings>=2.2" \
      "boto3>=1.34" \
      "sqlalchemy>=2.0" \
      "aiosqlite>=0.20" \
      "loguru>=0.7" \
      "fastapi>=0.110" \
      "uvicorn[standard]>=0.29" \
      "python-telegram-bot>=21" \
      "apscheduler>=3.10" \
      "anthropic>=0.34" \
      "pandas>=2.2" \
      "numpy>=1.26"

# ── Stage 2: runtime image ──────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="kuromi-trader" \
      org.opencontainers.image.description="Upbit 자동매매 시스템"

WORKDIR /app

# Copy installed packages from deps stage
COPY --from=deps /install /usr/local

# Copy application source
COPY src/   src/
COPY config/ config/

# Persistent volumes will be mounted here
RUN mkdir -p data logs

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    ENV=prod

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/state')"

CMD ["python", "-m", "src.main"]
