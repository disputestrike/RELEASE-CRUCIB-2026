# CrucibAI – production (Railway): backend + frontend in one image
# Build: docker build -t crucibai .
# Run:   docker run -p 8000:8000 -e DATABASE_URL=... -e JWT_SECRET=... crucibai

# Stage 1: build the frontend from source so Railway always ships a fresh bundle
# (the committed frontend/build/ is kept as a fallback but is no longer the
# source of truth — Stage 1 rebuilds from frontend/src on every deploy).
FROM node:22-alpine AS frontend
WORKDIR /app
# Copy the full frontend source BEFORE npm ci because package.json has a
# postinstall hook (`node scripts/patch-ajv-formats.js`) that runs during
# install and needs scripts/ (and the rest of the source) available.
COPY frontend/ ./
RUN npm ci --legacy-peer-deps --no-audit --no-fund --loglevel=error
# Build — ESLint disabled (CRA warnings don't break the bundle and we lint in CI).
ENV CI=true
ENV DISABLE_ESLINT_PLUGIN=true
ENV GENERATE_SOURCEMAP=false
RUN npm run build

# Stage 2: backend + serve built frontend static
FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y nodejs npm curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# curl: slim image has no curl — without it Docker HEALTHCHECK always fails (Railway marks service unhealthy).
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Single source of truth for Python deps (matches CI / local backend dev).
COPY backend/requirements.txt ./requirements.txt
RUN echo "Installing dependencies..." && pip install --no-cache-dir -r requirements.txt && echo "Dependencies installed successfully"
RUN python -m playwright install --with-deps chromium
WORKDIR /app
# Copy the backend directory AS backend to maintain module structure
COPY backend/ ./backend/
RUN echo "Backend files copied to /app/backend"
COPY --from=frontend /app/build ./backend/static
RUN echo "Frontend static files copied to /app/backend/static"
COPY proof/benchmarks/repeatability_v1/summary.json /proof/benchmarks/repeatability_v1/summary.json
COPY proof/benchmarks/repeatability_v1/PASS_FAIL.md /proof/benchmarks/repeatability_v1/PASS_FAIL.md
COPY proof/full_systems/summary.json /proof/full_systems/summary.json
COPY proof/full_systems/PASS_FAIL.md /proof/full_systems/PASS_FAIL.md
RUN echo "Benchmark and full systems proof files copied"

ENV PORT=8000
EXPOSE 8000

# App health is GET /api/health (not /health). Respect Railway $PORT for the probe.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8000}/api/health" >/dev/null || exit 1'

ENV PYTHONPATH=/app:/app/backend
CMD ["sh", "-c", "uvicorn backend.server:app --host 0.0.0.0 --port ${PORT:-8000}"]