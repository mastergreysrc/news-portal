# ============================================================
# News Portal — Multi-stage Docker build
# Stage 1: Build SvelteKit frontend
# Stage 2: Python backend + serve static frontend
# ============================================================

# --- Stage 1: Frontend build ---
FROM node:22-alpine AS frontend

WORKDIR /app/frontend

# Install deps (cached layer)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci 2>/dev/null || npm install

# Copy source and build
COPY frontend/ ./
RUN npm run build


# --- Stage 2: Backend + frontend ---
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Gaming News PL"
LABEL org.opencontainers.image.description="Polish gaming news aggregator"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps (cached layer)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend source
COPY backend/ ./backend/
COPY config.yaml ./

# Frontend build output from stage 1
COPY --from=frontend /app/frontend/build ./frontend/build

# Data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

WORKDIR /app/backend
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
