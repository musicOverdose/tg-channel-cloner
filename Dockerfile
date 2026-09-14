# ==============================================================================
# Telegram Channel Cloner - Production Multi-Stage Dockerfile
# ==============================================================================

# --- Stage 1: Build Frontend Assets ---
FROM node:20-alpine AS frontend-builder
WORKDIR /build

# Copy frontend source files
COPY frontend/ ./

# If package-lock.json exists, npm ci, else npm install
RUN if [ -f package.json ]; then \
      npm install --prefer-offline --no-audit || true; \
    fi

# If vite build script exists, build dist, otherwise assets are already in frontend/
RUN if [ -f package.json ] && grep -q '"build"' package.json; then \
      npm run build || true; \
    fi

# Ensure dist exists
RUN if [ ! -d dist ]; then \
      mkdir -p dist && cp -r src/* dist/ 2>/dev/null || true; \
      cp index.html dist/ 2>/dev/null || true; \
    fi


# --- Stage 2: Production Python Runtime ---
FROM python:3.12-slim AS runner

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_PORT=8083 \
    DATABASE_URL="sqlite+aiosqlite:////data/cloner.db" \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies (curl is used for docker healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Create persistent data directory
RUN mkdir -p /data

# Copy backend application code
COPY backend/ /app/backend/

# Copy built frontend assets into static directory
COPY --from=frontend-builder /build/dist /app/backend/app/static

# Expose web and API port
EXPOSE 8083

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8083/health || exit 1

# Launch production ASGI server
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8083", "--workers", "1"]
