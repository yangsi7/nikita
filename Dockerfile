# Nikita API - Cloud Run Deployment
# Multi-stage build for optimized image size

# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files for installation
COPY pyproject.toml README.md ./
COPY nikita/ ./nikita/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Stage 2: Runtime stage
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /app/nikita/ ./nikita/

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Cloud Run expects PORT environment variable
ENV PORT=8080

# Run with uvicorn
# - workers=1: Cloud Run handles scaling via instances
# - timeout-keep-alive=30: Match Cloud Run's idle timeout
CMD exec uvicorn nikita.api.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers 1 \
    --timeout-keep-alive 30
