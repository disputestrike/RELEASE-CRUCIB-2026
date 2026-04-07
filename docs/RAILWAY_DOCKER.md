# Railway + Docker (single image)

The repo **`Dockerfile`** builds one image: Node builds the React app, then Python serves **FastAPI** + static files under `/app/static`.

## What was breaking health checks

1. **`HEALTHCHECK` used `/health`** — the API exposes **`GET /api/health`** (see `backend/routers/health.py`). Wrong path → probe always fails → platform marks the service unhealthy.
2. **`python:*-slim` has no `curl`** — the probe command was `curl ...` so it failed even if the path were correct. **`curl` is now installed** in the image.
3. **Wrong `requirements.txt`** — the image now installs from **`backend/requirements.txt`** (same as CI), not the legacy root `requirements.txt`.

## Required env on Railway

- **`DATABASE_URL`** — Postgres (use Railway plugin or external URL).
- **`JWT_SECRET`** — long random string.
- **`REDIS_URL`** — optional but recommended for queues.
- **`PORT`** — set by Railway; the container CMD and health check use `${PORT}`.

Redeploy after pushing Dockerfile changes.
