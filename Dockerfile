# CrucibAI – production (Railway): backend + frontend in one image
# Build: docker build -t crucibai .
# Run:   docker run -p 8000:8000 -e DATABASE_URL=... -e JWT_SECRET=... crucibai

# Stage 1: build frontend (same-origin API: REACT_APP_BACKEND_URL="" => /api)
FROM node:22-alpine AS frontend
WORKDIR /app
# Copy package files + scripts + .npmrc so postinstall and peer-deps work
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
COPY frontend/scripts ./scripts
RUN npm ci --omit=optional --legacy-peer-deps
COPY frontend/ ./
ENV REACT_APP_BACKEND_URL=
ENV FAST_REFRESH=false
ENV NODE_ENV=production
RUN npm run build

# Stage 2: backend + serve frontend static
FROM python:3.11-slim-bookworm
WORKDIR /app

# curl: slim image has no curl — without it Docker HEALTHCHECK always fails (Railway marks service unhealthy).
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Single source of truth for Python deps (matches CI / local backend dev).
COPY backend/requirements.txt ./requirements.txt
RUN echo "Installing dependencies..." && pip install --no-cache-dir -r requirements.txt && echo "Dependencies installed successfully"

COPY backend/ ./
RUN echo "Backend files copied"
COPY --from=frontend /app/build ./static
RUN echo "Frontend static files copied"

ENV PORT=8000
EXPOSE 8000

# App health is GET /api/health (not /health). Respect Railway $PORT for the probe.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8000}/api/health" >/dev/null || exit 1'

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
