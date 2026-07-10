# Setup & Test Guide

Everything a new engineer needs to stand up **RT ERP** from a clean clone and verify it works.
For *what the project is and how it's built*, read **[PROJECT_CANON.md](./PROJECT_CANON.md)**.

---

## 1. Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Python | 3.12 | Everything (agents, Streamlit, backend) |
| Node.js | 20+ | Next.js frontend |
| Docker Desktop | latest | Web-app backend + Langfuse containers |
| Ollama | latest | **Optional** — only for the real local FinGPT forecaster engine |

**Accounts / keys you must supply:**
- **Azure OpenAI** — an endpoint + key with a `gpt-4o-mini` deployment (powers every agent).
- **Finnhub** — a free API key from [finnhub.io](https://finnhub.io) (Stock Forecaster market data).
- **Langfuse** — self-hosted; it comes up automatically via `docker compose` (no external account).

---

## 2. Configure environment

Create a `.env` file in the repo root with these keys (values not shown — get them from the project owner):

```bash
# Azure OpenAI (all agents)
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# Market data (Stock Forecaster)
FINNHUB_API_KEY=

# Langfuse observability (self-hosted via docker compose)
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

`core/config.py` loads this `.env` once from an absolute path, so it works regardless of where you run from.

The frontend is already configured — `frontend/.env.local` contains `NEXT_PUBLIC_API_URL=http://localhost:8000`.

---

## 3. Install

```bash
# Python (agents + backend)
pip install -r requirements.txt -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

> The **backend Docker image** bakes its own Python deps at build time, so the `pip install` above is
> only needed to run Streamlit or the backend on the host directly.

---

## 4. Run — pick the path that fits

### A. Streamlit ERP — simplest, no Docker (great first smoke test)
One process; calls the Python agents in-process.
```bash
streamlit run app.py            # → http://localhost:8501
```

### B. Web app (Next.js + FastAPI) — the production-style UI
Backend + Langfuse run in Docker; the frontend runs on the host for fast HMR.
```bash
docker compose up -d --build                 # backend :8000 + Langfuse :3000 (+ its DB)
cd frontend && npm run dev -- --port 3001    # → http://localhost:3001
# stop containers when done:
docker compose down
```
Or start both at once from the repo root:
```bash
./dev.sh
```
> Rebuild the backend image (`docker compose up -d --build backend`) whenever you change Python code —
> the image copies `core/`, `modules/`, `backend/` at build time.

### C. FinGPT forecaster engine — optional (real local model)
Only needed if you want the Stock Forecaster's **FinGPT** engine (the Azure engine works without this).
```bash
./fingpt-service/setup_model.sh              # one-time: pulls an ungated GGUF, creates the Ollama model
# then Ollama + the proxy service (./dev.sh starts these automatically if Ollama is installed):
ollama serve &
cd fingpt-service && python3 -m uvicorn main:app --port 8001
```

### Ports

| Service | Port | Path |
|---|---|---|
| FastAPI backend | 8000 | Docker (`docker compose`) |
| Langfuse UI | 3000 | Docker |
| FinGPT service | 8001 | host (optional) |
| Next.js frontend | 3001 | host (`npm run dev`) |
| Streamlit ERP | 8501 | host (`streamlit run app.py`) |

> Frontend is on 3001 because Langfuse owns 3000.

---

## 5. Test it

### Automated (no keys/network needed — the LLM is mocked)
```bash
pytest tests/          # → 40 passed
```
Covers the agent pipelines, the deterministic reports, the ground-truth hallucination guard, and the
6-agent suite (10 scenarios each).

### Backend smoke (with the web-app stack running)
```bash
curl http://localhost:8000/api/health                               # {"status":"ok"}
curl http://localhost:8000/api/finance/alerts        | python3 -m json.tool | head   # 37 alerts, mixed risk
curl http://localhost:8000/api/finance-suite/ap/scenarios            # 10 scenarios
curl "http://localhost:8000/api/finance-suite/ap/report?scenario=overdue-vendor"
```
Interactive API docs: **http://localhost:8000/docs**.

### Frontend click-through (http://localhost:3001)
- **Finance → Alert Queue** → click a **High** account (e.g. `ACC-00089`) → confirm the **"Why this
  account is flagged"** card (score breakdown) and the **bold, red-tinted flagged transactions** with
  VELOCITY/GEO badges.
- **Finance AI Suite → any agent** → pick a scenario → the report updates → ask a question in the chat
  and watch the Data → Ground Truth → Audit → Synthesis stage badges.
- **Finance AI Suite → Finance Copilot** → ask something cross-domain ("compare AP vs AR overdue") →
  it pulls multiple reports before answering.
- **Trading → Stock Forecaster** → toggle **Azure** ↔ **FinGPT** (FinGPT needs path C running).

### Observability
Open **http://localhost:3000** (Langfuse) after running a chat to see one trace per run with a
generation/span for each pipeline stage.

---

## 6. Regenerate the mock data (optional)

All mock datasets are reproducible from seeded generators:
```bash
python3 -m modules.finance_suite.scripts.generate_scenarios   # 6 suite agents × 10 scenarios
python3 -m modules.finance.scripts.diversify_risk             # inject Medium-risk accounts into the alert queue
python3 -m modules.finance.scripts.generate_invoices          # invoice-fraud dataset
python3 -m modules.trading.scripts.generate_trading_data      # positions / trades / prices
```

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `curl` connection refused / `docker compose ps` empty | Docker Desktop isn't running → `open -a Docker`, then `docker compose up -d`. |
| Backend not reflecting Python changes | Rebuild the image: `docker compose up -d --build backend`. |
| Langfuse "no public_key" / flush warnings in logs | Harmless when Langfuse isn't reachable; the run still completes. Check `LANGFUSE_*` in `.env` if you want traces. |
| Chat errors but reports still show | Azure creds missing/unreachable. The **deterministic reports need no LLM** and still render; fix `AZURE_OPENAI_*`. |
| Port 3000 already in use | Langfuse owns 3000; the frontend runs on **3001** by design. |
| FinGPT engine returns 503 | Ollama or `fingpt-service` (:8001) isn't running — start path C, or use the Azure engine. |

---

**Deeper reading:** [`WEBAPP.md`](./WEBAPP.md) (web-app internals), [`README.md`](./README.md)
(Streamlit app + module logic), [`PROJECT_CANON.md`](./PROJECT_CANON.md) (architecture + features).
