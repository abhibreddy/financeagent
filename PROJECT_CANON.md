# Project Canon — RT ERP

The single source of truth for **what RT ERP is** and **how it's built**. For setup/run/test steps,
see **[SETUP.md](./SETUP.md)**.

---

## Overview

RT ERP is a **2-module ERP** — **Finance** (fraud detection) and **Trading** (portfolio analytics) —
plus a **Finance AI Suite** of six finance-operations agents. It is served through **two front ends**
that sit over **one shared Python core**:

1. a **Streamlit ERP** (`app.py`) — the original all-in-one app, and
2. a **Next.js + FastAPI web app** (`frontend/` + `backend/`) — the production-style UI.

All business logic lives once in `modules/` + `core/`; both front ends call the same functions, so
there is no logic duplication. Every AI feature is an LLM agent traced end-to-end in Langfuse, and the
data stages are deterministic so the agents can't hallucinate the numbers.

---

## Architecture

```
                         ┌───────────────────────────── shared Python core ─────────────────────────────┐
                         │  core/            config (dotenv+paths), llm (Azure factory), tracing, ui      │
                         │  modules/finance        fraud logic + 3-stage agent + invoice detectors        │
                         │  modules/finance_suite   6 config-driven agents on one engine + tool-calling    │
                         │  modules/trading         portfolio metrics + agent + FinGPT-style forecaster    │
                         └──────────────┬───────────────────────────────────────────┬───────────────────┘
                                        │                                           │
                     ┌──────────────────▼─────────────┐          ┌──────────────────▼──────────────────┐
                     │  app.py  (Streamlit ERP :8501) │          │  backend/ (FastAPI :8000, Docker)   │
                     │  st.navigation over the modules│          │  JSON + SSE, wraps modules/ verbatim │
                     └────────────────────────────────┘          └──────────────────┬──────────────────┘
                                                                                     │ HTTP/JSON + SSE
                                                                  ┌──────────────────▼──────────────────┐
                                                                  │  frontend/ (Next.js :3001, shadcn)  │
                                                                  └─────────────────────────────────────┘

   Langfuse (:3000, Docker) traces every agent run.   fingpt-service/ (:8001, host) → Ollama, for the real FinGPT model.
```

## Repo layout

| Path | What it is |
|---|---|
| `core/` | Shared: `config.py` (one dotenv + absolute paths), `llm.py` (`make_azure_llm`), `tracing.py` (`get_langfuse`), `ui.py` (Streamlit CSS) |
| `modules/finance/` | Fraud platform — `utils.py` (velocity/risk, invoice detectors, SQLite decisions), `agent.py` (3-stage fraud agent), `invoice_agent.py`, `pages/` (Streamlit), `data/` (CSVs), `scripts/` |
| `modules/finance_suite/` | Finance AI Suite — `engine.py` (`run_suite_agent`), `specs.py` (6 agent specs), `data.py` (deterministic reports + ground-truth verify), `scenarios.py`, `copilot.py` (tool-calling), `data/*.json` (scenarios), `pages/` |
| `modules/trading/` | Trading — `utils.py` (portfolio metrics), `trading_agent.py` (3-stage), `forecaster.py` (Azure/FinGPT), `data/` (CSVs) |
| `backend/` | FastAPI app — `main.py` (CORS, routers), `routers/{finance,finance_suite,trading,agents}.py`, `serializers.py`, `sse.py`, `Dockerfile` |
| `frontend/` | Next.js app — `app/**/page.tsx`, `components/` (shadcn + app-shell + agent-chat), `lib/{api,types,useAgentStream}.ts` |
| `fingpt-service/` | Host FastAPI (:8001) → Ollama; runs the real FinGPT-Forecaster model (`Modelfile`, `setup_model.sh`) |
| `tests/` | Pytest (40) — deterministic, LLM mocked |
| `graphify-out/` | Auto-generated code knowledge graph (`GRAPH_REPORT.md`) |

---

## The agent pipeline pattern

Every AI feature follows the same shape (implemented once per module, config-driven in the suite):

```
User prompt → Stage 1: Data  → Ground-Truth Verifier → Stage 2: Audit (LLM) → Stage 3: Synthesis (LLM) → Answer
              (deterministic)   (deterministic re-check)
```

- **Stage 1 (Data)** is deterministic — a direct tool/function call (fraud) or a computed report
  (suite). Nothing is invented here.
- **Ground-Truth Verifier** re-runs the computation and diffs it against what will be reasoned over;
  any mismatch is flagged as a hallucination. This is the core anti-hallucination mechanism
  (`_verify_data_summary` in fraud, `verify_report` in the suite).
- **Stages 2–3** are LLM calls (Azure `gpt-4o-mini`) that review and write the final answer.
- Each stage is a Langfuse **generation/span**, so runs are fully traceable.

The **Finance Copilot** is a variant: its Stage 1 is a **tool-calling** LangGraph agent that decides
which agents' reports to pull (`list_finance_data`, `get_finance_report`) — but the tools still return
deterministic reports, so the data layer remains hallucination-free.

---

## Feature catalog

### Finance (fraud)
- **Dashboard** — KPIs, risk distribution, recent flagged events.
- **Alert Queue** — risk-ranked accounts (**High / Medium / Low** diversity), with Block / Clear /
  Escalate / Monitor decisions persisted to SQLite.
- **Account Detail** — full risk profile with a **"Why this account is flagged"** explainer (per-driver
  score breakdown: velocity / geo / known-fraud) and **flagged-transaction highlighting** (bold rows +
  VELOCITY/GEO badges).
- **Invoice Fraud** — 5 detectors (exact dups, near dups, split billing, threshold avoidance, ghost vendors).
- **Fraud Agent Chat** — the 3-stage pipeline over a conversational interface.

### Finance AI Suite
Six agents on **one shared `run_suite_agent` engine**, each with **10 selectable mock scenarios**:

| Agent | Computes |
|---|---|
| **AP** | Aging buckets, overdue, early-pay discounts, duplicate-PO risk |
| **AR** | DSO, aging, at-risk receivables, dunning priority |
| **Cash Flow** | 13-week forecast, runway, liquidity risk |
| **Reconciliation** | Bank-vs-ledger match rate, break analysis |
| **Financial Insights** | KPIs, margins, budget variance |
| **Copilot** | Tool-calling assistant that pulls any of the above reports on demand |

Each analytical agent's report is deterministic and doubles as its own ground truth.

### Trading
- **Portfolio Dashboard** — metrics, sector exposure, price charts.
- **Portfolio Agent** — 3-stage portfolio analysis.
- **Stock Forecaster** — single-stock outlook with an **Azure ↔ real FinGPT** toggle (see below).

---

## LLM routing

Every agent runs on **Azure OpenAI** via `core/llm.py::make_azure_llm` (`gpt-4o-mini`). The **only**
exception is the **Stock Forecaster**, which can toggle to the **actual FinGPT-Forecaster model**
(Llama-2-7b) run locally via Ollama behind `fingpt-service/`. Both engines sit behind the same
`POST /api/trading/forecast` endpoint (`engine: "azure" | "fingpt"`).

---

## Data layer

All paths resolve from `core/config.py` (env-overridable):
- **Finance** — `accounts.csv`, `transactions.csv`, `invoices.csv`; analyst decisions in SQLite
  (`fraudguard.db`, `alert_decisions`).
- **Finance Suite** — `modules/finance_suite/data/<agent>.json`, 10 scenarios each (Copilot has none).
- **Trading** — `positions.csv`, `trades.csv`, `prices.csv`; live market data via Finnhub + yfinance.

All datasets are reproducible from seeded generators in `modules/*/scripts/` (see SETUP.md §6).

---

## Two front ends

| | Streamlit ERP | Next.js + FastAPI |
|---|---|---|
| Entry | `app.py` (`st.navigation`) | `frontend/` → `backend/` |
| Run | `streamlit run app.py` (:8501) | `docker compose up -d` + `npm run dev` (:3001 → :8000) |
| Calls modules | in-process | over HTTP/JSON + SSE |

**Backend endpoints:** `/api/finance/*`, `/api/finance-suite/*`, `/api/trading/*` (JSON) and
`/api/agents/{finance,invoice,trading}/stream` + `/api/agents/suite/{agent}/stream` (SSE staged reveal).

---

## Tech stack

| Layer | Tech |
|---|---|
| Agents | LangGraph, LangChain, Azure OpenAI (`gpt-4o-mini`) |
| Forecaster (optional) | FinGPT-Forecaster (Llama-2-7b) via Ollama |
| Data | pandas, SQLite, Finnhub + yfinance |
| Observability | Langfuse v2 (self-hosted, Docker) |
| Streamlit UI | Streamlit ≥1.36, Plotly |
| Web UI | Next.js 16 / React 19 / Tailwind v4 / shadcn/ui / recharts |
| API | FastAPI, uvicorn, sse-starlette |
| Infra | Docker Compose (backend + Langfuse + Postgres) |

---

## Key design decisions

- **Config-driven suite engine, not 6 cloned pipelines** — one `run_suite_agent` + 6 small specs;
  adding a 7th agent is a spec + a report function + a scenario file.
- **Deterministic data = ground truth** — Stage 1 computes exact numbers, so there's no hallucination
  surface, and the ground-truth verifier is a free, testable guard.
- **Two front ends over one core** — logic lives once in `modules/`+`core/`; Streamlit and FastAPI both
  call it, so features never drift between UIs.
- **FinGPT runs locally via an ungated pre-merged GGUF** — no HF token, no GPU-only torch path; the
  process/host boundary matches the container boundary via `fingpt-service/`.

---

## Testing

`pytest tests/` → **40 passing**, all deterministic (LLM mocked, no network): agent pipelines return
the expected tuple shapes, reports are deterministic, and the ground-truth guard both passes clean
reports and catches tampered values.

---

## Pointers

- **[SETUP.md](./SETUP.md)** — install, run, test from a clean clone.
- **[WEBAPP.md](./WEBAPP.md)** — Next.js + FastAPI internals, endpoints, FinGPT engine.
- **[README.md](./README.md)** — Streamlit app + deep module logic.
- **`graphify-out/GRAPH_REPORT.md`** — auto-generated code graph (god nodes, communities).
