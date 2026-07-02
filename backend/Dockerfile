# Backend container — runs the FastAPI app (uvicorn) that wraps the existing Python logic.
# Build context is the repo root so modules/, core/, and the data files are available.
#   docker compose build backend
FROM python:3.12-slim

WORKDIR /app

# System libs some wheels need at runtime (curl_cffi, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching.
COPY requirements.txt ./requirements.txt
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r backend/requirements.txt

# App code (reused Python logic + FastAPI). .dockerignore keeps this lean.
COPY core ./core
COPY modules ./modules
COPY backend ./backend

EXPOSE 8000

# Production server. --host 0.0.0.0 so it's reachable from outside the container.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
