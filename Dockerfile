# CrucibAI – production (Railway): backend + frontend in one image
# Build: docker build -t crucibai .
# Run:   docker run -p 8000:8000 -e MONGO_URL=... -e JWT_SECRET=... crucibai

# Stage 1: build frontend (same-origin API: REACT_APP_BACKEND_URL="" => /api)
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json frontend/yarn.lock* ./
RUN npm ci --omit=optional 2>/dev/null || yarn install --frozen-lockfile
COPY frontend/ ./
ENV REACT_APP_BACKEND_URL=
RUN npm run build 2>/dev/null || yarn build

# Stage 2: backend + serve frontend static
FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /app/build ./static

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
