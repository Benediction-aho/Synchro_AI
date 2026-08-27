# SYNCHRO Backend - Multi-stage Dockerfile
# Base image with security updates
FROM python:3.12-slim-bookworm AS base

# Security: Update packages and remove unnecessary ones
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r synchro && useradd -r -g synchro synchro

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# ============================================================
# API Gateway
# ============================================================
FROM base AS api-gateway

# Copy application code
COPY src/ ./src/

# Create required directories
RUN mkdir -p /app/data /app/logs && chown -R synchro:synchro /app

USER synchro

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "synchro.services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]


# ============================================================
# Data Ingestion Service
# ============================================================
FROM base AS data-ingestion

COPY src/ ./src/

RUN mkdir -p /app/data /app/logs && chown -R synchro:synchro /app

USER synchro

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "synchro.services.data_ingestion.main"]


# ============================================================
# Learning Worker
# ============================================================
FROM base AS learning-worker

COPY src/ ./src/

RUN mkdir -p /app/data /app/logs && chown -R synchro:synchro /app

USER synchro

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "synchro.services.learning_worker.main"]


# ============================================================
# Evolution Worker
# ============================================================
FROM base AS evolution-worker

COPY src/ ./src/

RUN mkdir -p /app/data /app/logs && chown -R synchro:synchro /app

USER synchro

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "synchro.services.evolution_worker.main"]


# ============================================================
# MQL5 Bridge
# ============================================================
FROM base AS bridge

COPY ../mql5_bridge/bridge/ ./src/

RUN mkdir -p /app/data /app/logs /app/config /app/state && chown -R synchro:synchro /app

USER synchro

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "src.main"]