# Stage 1: Builder
FROM python:3.11-slim AS builder

# uv is pinned to the same version CI uses (see UV_VERSION in ci.yml)
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv

WORKDIR /app

# Install the exact resolution recorded in uv.lock. --frozen fails the build
# if the lock is stale rather than silently resolving something else, so the
# image can only ever contain what CI tested.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Runtime
FROM python:3.11-slim

# The venv must live at the same path it was built at: its scripts and
# pyvenv.cfg hold absolute paths.
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app/ ./app/
COPY .env.example .env

ENV PATH=/app/.venv/bin:$PATH
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
