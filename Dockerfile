# CrucibAI – production (Railway): backend + frontend in one image
# Build: docker build -t crucibai .
# Run:   docker run -p 8000:8000 -e DATABASE_URL=... -e JWT_SECRET=... crucibai

# Stage 1: build frontend (same-origin API: REACT_APP_BACKEND_URL="" => /api)
FROM node:20-alpine AS frontend
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
FROM python:3.11.0-slim
WORKDIR /app

# Cache-bust: force rebuild - timestamp: 2026-03-04-1937
RUN echo "Build: 2026-03-04"

COPY requirements.txt .
RUN echo "Installing dependencies..." && pip install --no-cache-dir -r requirements.txt && echo "Dependencies installed successfully"
COPY backend/ ./
RUN echo "Backend files copied"
COPY --from=frontend /app/build ./static
RUN echo "Frontend static files copied"

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
