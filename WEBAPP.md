# RT ERP — Web App (Next.js + FastAPI)

A production-grade frontend for the RT ERP, matching the `Styling/` shadcn design language.
It runs **alongside** the existing Streamlit app (which is untouched and still works via
`streamlit run app.py`).

## Architecture

```
Next.js frontend (React 19, Tailwind v4, shadcn/ui)   ── HTTP/JSON + SSE ──►   FastAPI backend
  frontend/                                                                     backend/
    app/            pages (Home, Finance, Trading)                               main.py        app + CORS
    components/ui/  shadcn primitives                                            routers/       finance, trading, agents
    components/     app-shell (sidebar), stat-card, agent-chat, markdown         serializers.py DataFrame/Timestamp → JSON
    lib/            api.ts (typed client), types.ts, useAgentStream.ts           sse.py         staged pipeline reveal
```

The backend **reuses all existing Python logic verbatim** — `modules/finance/*`,
`modules/trading/*`, `core/*`. No logic was rewritten; FastAPI only wraps it and serializes.

## Endpoints

Plain JSON: `/api/finance/{alerts,accounts/{id},accounts/compare,decisions,invoices/report}`,
`/api/trading/{portfolio,positions,prices/{ticker},forecast}`.
SSE streams (Data→Audit→Synthesis reveal): `/api/agents/{finance,invoice,trading}/stream`.
Interactive docs at `http://localhost:8000/docs`.

## Pages (parity with the Streamlit app)

| Route | Purpose |
|---|---|
| `/` | Home — two clickable module cards |
| `/finance/dashboard` | KPIs, risk distribution, recent events |
| `/finance/alerts` | Alert queue with Block/Clear/Escalate/Monitor (persists to SQLite) |
| `/finance/accounts` `/finance/accounts/[id]` | Account lookup + full risk profile |
| `/finance/invoices` | Invoice fraud — 5 detection categories |
| `/finance/chat` | Fraud agent chat (SSE, live pipeline) |
| `/trading/dashboard` | Portfolio metrics + sector exposure + price charts (recharts) |
| `/trading/agent` | Portfolio agent chat (SSE) |
| `/trading/forecaster` | Single-stock outlook — **two engines**: Azure (reimplementation) or **real FinGPT** (local Ollama). Needs `FINNHUB_API_KEY` |

## Running

**Backend runs in Docker** (`backend/Dockerfile`, wired into `docker-compose.yml` alongside
Langfuse). **Frontend runs on the host** (Next.js, fast HMR).

One-time:
```bash
cd frontend && npm install && cd ..     # frontend deps (backend deps are baked into its image)
```

From the repo root:
```bash
./dev.sh          # docker compose up (backend :8000 + Langfuse :3000) + Next.js (:3001)
```
Or manually:
```bash
docker compose up -d --build backend langfuse-server    # containers
cd frontend && npm run dev -- --port 3001               # frontend on host
# stop containers: docker compose down
```

Ports: **backend :8000**, **Langfuse :3000**, **frontend :3001** (3001 avoids Langfuse's 3000).

- Frontend reads `frontend/.env.local` → `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- The **backend container** gets its secrets from the repo-root `.env` via `env_file` in compose.
  Compose overrides `LANGFUSE_HOST=http://langfuse-server:3000` (service name, not localhost) and
  `FINANCE_DB=/data/fraudguard.db` (a named volume `backend_data`, so analyst decisions persist).
- CORS allows `:3001`/`:3000` by default; override with the `FRONTEND_ORIGINS` env var.

### Iterating on backend code
The image copies `core/`, `modules/`, `backend/` at build time. After changing Python, rebuild:
`docker compose up -d --build backend`. For rapid iteration you can still run it on the host with
hot-reload instead: `python3 -m uvicorn backend.main:app --reload --port 8000`.

## FinGPT engine (Stock Forecaster)

The Stock Forecaster has two selectable engines behind the same `POST /api/trading/forecast`
endpoint (`engine: "azure" | "fingpt"`):

- **Azure** — FinGPT-Forecaster's *methodology* (prompt + Finnhub/yfinance data) run on Azure `gpt-4o-mini`. Fast, reliable, default.
- **FinGPT** — the **actual fine-tuned FinGPT-Forecaster model** (Llama-2-7b), run **locally via Ollama**.

Architecture: the backend builds the FinGPT prompt (Finnhub + yfinance) and proxies it to a
small host-run **`fingpt-service/`** (FastAPI :8001), which calls Ollama. The service + Ollama
run on the **host** (the containerized backend reaches them via `host.docker.internal:8001`,
set by `FINGPT_SERVICE_URL` in compose). If the service/Ollama is down, `engine: "fingpt"`
returns **503** with a "use Azure" message; the Azure engine is unaffected.

One-time model setup (free, no HF token — uses an ungated pre-merged GGUF):
```bash
./fingpt-service/setup_model.sh      # pulls the GGUF, creates `fingpt-forecaster` in Ollama, warms it
```
Runtime (started automatically by `./dev.sh` if Ollama is present):
```bash
ollama serve &                                                   # if not already running
cd fingpt-service && python3 -m uvicorn main:app --port 8001     # the proxy service
```
The FinGPT engine caps `weeks` at 3 (its context is `num_ctx 4096`); typical latency ~10–30s.

## Notes
- Chat is stateless: the client round-trips the full `messages` array each turn.
- SSE is a "staged reveal" — the agents compute all at once, then stream stages for the UI.
  True token streaming would require the agents to `yield` (future enhancement).
- Deployment (Docker/hosting) is intentionally out of scope for now.
