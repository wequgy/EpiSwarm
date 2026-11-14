# Multi-stage Dockerfile for EpiSwarm Platform
# Stage 1: Build modern web frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: Python simulation backend and production runtime
FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

# Copy application code, packs, and evidence
COPY src/ ./src/
COPY regions/ ./regions/
COPY diseases/ ./diseases/
COPY scenarios/ ./scenarios/
COPY behavior/ ./behavior/
COPY evidence/ ./evidence/
COPY docs/ ./docs/

# Copy built frontend dist from Stage 1
COPY --from=frontend-builder /web/dist ./web/dist

EXPOSE 8000

CMD ["uvicorn", "episwarm.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
