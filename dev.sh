#!/usr/bin/env bash
# dev.sh — run the app for local dev.
#   Backend + Langfuse: Docker containers (docker compose)
#   Frontend:           Next.js on the host (fast HMR)
# The existing Streamlit app is independent (streamlit run app.py) and unaffected.
set -euo pipefail
cd "$(dirname "$0")"

echo "→ Backend:  http://localhost:8000  (Docker: backend)"
echo "→ Langfuse: http://localhost:3000  (Docker: langfuse-server)"
echo "→ FinGPT:   http://localhost:8001  (host: FinGPT service + Ollama)"
echo "→ Frontend: http://localhost:3001  (Next.js on host)"
echo ""

# FinGPT engine (host): Ollama + the FinGPT service. Skipped gracefully if Ollama is absent;
# the forecaster's Azure engine still works without it.
if command -v ollama >/dev/null 2>&1; then
  ollama list >/dev/null 2>&1 || (ollama serve >/tmp/ollama.log 2>&1 &)
  if ! ollama list 2>/dev/null | grep -q fingpt-forecaster; then
    echo "  (one-time) run ./fingpt-service/setup_model.sh to install the FinGPT model"
  fi
  (cd fingpt-service && python3 -m uvicorn main:app --host 0.0.0.0 --port 8001 >/tmp/fingpt.log 2>&1 &)
else
  echo "  Ollama not found — FinGPT engine disabled; the Azure forecaster still works."
fi

# Backend + Langfuse in containers. --build picks up code changes.
docker compose up -d --build backend langfuse-server

# Frontend on the host, port 3001 (3000 is taken by Langfuse). Ctrl+C stops it;
# containers keep running — stop them with: docker compose down
cd frontend && npm run dev -- --port 3001
