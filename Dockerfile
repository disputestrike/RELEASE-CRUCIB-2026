# CrucibAI Backend – production (Railway, Render, Fly.io, etc.)
# Build: docker build -t crucibai-backend .
# Run:   docker run -p 8000:8000 -e MONGO_URL=... -e JWT_SECRET=... crucibai-backend

FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

ENV PORT=8000
EXPOSE 8000

# Railway sets PORT at runtime; use shell so it is expanded
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
