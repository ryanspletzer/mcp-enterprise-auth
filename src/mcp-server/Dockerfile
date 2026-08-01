# Multi-stage Docker build for MCP Server

# Stage 1: Builder
FROM python:3.11-slim AS builder

# uv is pinned to the same version CI uses (see UV_VERSION in ci.yml)
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv

# Set working directory. The venv is built here and copied to the same path
# in the runtime stage: its scripts and pyvenv.cfg hold absolute paths.
WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the exact resolution recorded in uv.lock. --frozen fails the build
# if the lock is stale rather than silently resolving something else, so the
# image can only ever contain what CI tested.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: Runtime
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash mcpuser

# Copy the resolved environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app/ /app/app/

# Set ownership
RUN chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Put the venv first on PATH
ENV PATH=/app/.venv/bin:$PATH

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
