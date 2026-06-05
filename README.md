# FraudGuard — Intelligent Fraud Detection Platform

A production-quality fraud detection platform built with Streamlit, LangGraph, Ollama, and Langfuse. Combines a real-time alert queue, a conversational AI investigation agent, and an invoice fraud scanner — all running fully locally with self-hosted LLM and observability infrastructure.

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Agent Pipeline](#agent-pipeline)
- [Hallucination Reduction System](#hallucination-reduction-system)
- [Invoice Fraud Detection](#invoice-fraud-detection)
- [Risk Scoring](#risk-scoring)
- [Observability (Langfuse)](#observability-langfuse)
- [UI Design](#ui-design)
- [Tech Stack](#tech-stack)
- [Setup](#setup)
- [Every Session](#every-session)
- [Project Structure](#project-structure)
- [Agent Tools Reference](#agent-tools-reference)
- [Environment Variables](#environment-variables)

---

## Features

| Feature | Description |
|---|---|
| **Dashboard** | Landing page with live metrics, feature navigation cards, and recent Langfuse trace activity |
| **Alert Queue** | Ranked list of all flagged accounts sorted by risk score. One-click block / clear / escalate / monitor with analyst attribution and undo |
| **Account Lookup** | Deep-dive view: velocity metrics, geo flags, dormancy signals, transaction timeline, multi-account comparison |
| **Agent Chat** | Conversational fraud investigation powered by a 3-stage LangGraph pipeline running locally via Ollama |
| **Invoice Fraud** | Automated invoice audit: duplicate detection, split billing, threshold avoidance, ghost vendor identification |
| **Observability** | Every agent run traced to self-hosted Langfuse v2 — latency, token usage, session history, stage-by-stage visibility |
| **Pipeline Debug Panel** | In-app expander showing every stage's raw output + ground truth verification result after each investigation |

---

## Architecture Overview

```
account_lookup.py            ← Streamlit entry point / Dashboard
├── pages/alert_queue.py     ← Alert Queue page
├── pages/2_Agent_Chat.py    ← Conversational agent page
└── pages/3_Invoice_Fraud.py ← Invoice fraud analysis page

agent.py                     ← Velocity fraud 3-stage pipeline
invoice_agent.py             ← Invoice fraud 3-stage pipeline
utils.py                     ← Velocity computation, risk scoring, SQLite decisions, invoice detectors
components.py                ← Shared sidebar nav component
css/style.css                ← Global dark-themed UI styles

synthetictables/
├── transactions.csv          ← Synthetic transaction data
├── accounts.csv              ← Synthetic account data
└── invoices.csv              ← Synthetic invoice data

fraudguard.db                ← SQLite (local only, gitignored) — analyst decisions
```

### Design Principles

**Separation of concerns across agents.** Data collection, audit/reasoning, and synthesis are three fully independent agents with distinct roles. No agent does more than one job.

**LLM used only where reasoning is needed.** Data collection for account investigations is handled entirely in Python — not via LLM tool-calling. The LLM only touches audit reasoning and final report synthesis. This eliminates a whole class of reliability problems.

**Deterministic ground truth before LLM reasoning.** Every account investigation runs a database-level verification pass before the Audit Agent sees any data. Discrepancies are surfaced as confirmed hallucinations rather than discovered after the fact.

**Self-hosted everything.** LLM (Ollama), observability (Langfuse v2 Docker), and data (SQLite + CSV) all run locally. No external API calls required at runtime.

---

## Agent Pipeline

Both the velocity fraud agent (`agent.py`) and the invoice fraud agent (`invoice_agent.py`) follow the same 3-stage pattern:

```
User prompt
     │
     ▼
┌──────────────────────┐
│  Stage 1: Data Agent  │  ← Collects raw facts (direct Python calls or LangGraph)
└──────────────────────┘
     │
     ▼
┌──────────────────────────────────┐
│  Ground Truth Verifier            │  ← Deterministic DB check (velocity agent only)
│  (no LLM — pure Python + regex)  │
└──────────────────────────────────┘
     │
     ▼
┌───────────────────────┐
│  Stage 2: Audit Agent  │  ← Receives data + ground truth report, flags issues
└───────────────────────┘
     │
     ▼
┌──────────────────────────┐
│  Stage 3: Synthesis Agent │  ← Writes analyst-ready structured report
└──────────────────────────┘
     │
     ▼
Final report → Streamlit chat bubble
```

### Stage 1 — Data Agent (velocity fraud)

When the query contains an account ID (`ACC-XXXXX`), all tools are called directly in Python via `_direct_account_investigation()`. This bypasses LLM tool-routing entirely. The LangGraph tool-calling agent is only used for open-ended questions that don't target a specific account.

**Why direct invocation:** Small local models (even 14B) are unreliable at chaining 3–4 sequential tool calls correctly. They may skip `analyze_velocity`, call tools out of order, or stop early. Direct Python invocation guarantees all data is always collected.

### Stage 2 — Audit Agent

Receives the full data summary plus the ground truth verification report. Its job is to cross-check conclusions against verified numbers, flag any discrepancy between what the Data Agent wrote and what the database says, and rate each key finding as Confirmed / Uncertain / Hallucination.

### Stage 3 — Synthesis Agent

Receives the original request, the data summary, and the audit review. Writes the final structured report. Its prompt is strictly constrained: no parenthetical notes explaining where values came from, no "Not available" for any field present in the data, no trailing commentary after the final `---`.

---

## Hallucination Reduction System

This is the core reliability innovation in FraudGuard. Three layers work together.

### Layer 1 — Deterministic Data Collection

`_direct_account_investigation(account_id)` in `agent.py` calls all tools via `.invoke()` directly from Python:

```python
acc_raw      = lookup_account.invoke({"account_id": account_id})
velocity_raw = analyze_velocity.invoke({"account_id": account_id})
txn_raw      = get_transaction_history.invoke({"account_id": account_id, "limit": 10})
```

The LLM never touches data collection for known account IDs. There is no chance of the model skipping a tool call or misrouting a tool argument. If risk level is High, `get_similar_flagged_accounts` is also called.

### Layer 2 — Ground Truth Verifier

`_verify_data_summary(data_summary)` runs after Stage 1, before Stage 2. It:

1. Regex-extracts the account ID from the summary text
2. Re-runs `compute_velocity()` against the actual database
3. Regex-parses 6 key numeric claims from the summary text
4. Compares each claimed value to the actual computed value

If all values match:
```
GROUND TRUTH VERIFIED for ACC-00009: max_velocity=10, risk_score=100,
risk_level=High, geo_flags=13, total_txns=40, total_amount=$108,010.94.
All values match the database.
```

If there are discrepancies:
```
GROUND TRUTH DISCREPANCIES — the following values in the Data Agent summary
do not match the database. Treat these as hallucinations and use the actual values:
  - geo_flags: claimed 5, actual 13 ← MISMATCH
```

This report is injected directly into the Audit Agent's input. The Audit Agent's prompt instructs it to treat ground truth values as authoritative.

### Layer 3 — Constrained Synthesis Prompt

The Synthesis Agent prompt uses angle-bracket fill instructions (`<account ID from ACCOUNT SUMMARY>`) rather than bracket placeholders, which small models tend to copy literally into their output. Hard rules in the prompt:

- Never write parenthetical notes like `(from ACCOUNT SUMMARY)`
- Never write `Not available` for any field present in the data
- Velocity threshold is always 5 — never any other number
- Stop after the final `---`, no trailing notes or commentary

The debug panel in Agent Chat shows all three layers after every run. Ground truth verification appears as a green success banner (verified) or red error banner (discrepancies).

---

## Invoice Fraud Detection

`invoice_agent.py` runs the same 3-stage pipeline with invoice-specific tools and detection logic implemented in `utils.py`.

### Detection Passes

| Pass | Logic | Threshold |
|---|---|---|
| **Exact duplicates** | Same vendor + amount + date | Any match |
| **Near duplicates** | Same vendor, amount within 1%, within 3 days | Configurable |
| **Split billing** | Vendor submits 4+ invoices within 7 days | `SPLIT_MIN_COUNT=4`, `SPLIT_WINDOW_DAYS=7` |
| **Threshold avoidance** | Invoice between $9,500–$9,999.99 | `APPROVAL_THRESHOLD=10000`, `THRESHOLD_BAND=500` |
| **Ghost vendors** | Vendor appears in fewer than 3 invoices total | Frequency < 3 |

### Invoice Tools

- `get_invoice_summary` — dataset overview (count, spend, vendor breakdown, date range)
- `find_duplicate_invoices` — exact and near-duplicate detection with total exposure
- `find_split_billing` — invoice splitting detection grouped by vendor
- `find_threshold_avoidance` — invoices clustered just below approval limit
- `find_ghost_vendors` — rare/fictitious vendor detection

---

## Risk Scoring

All accounts are scored 0–100 using a weighted combination of signals computed in `utils.compute_velocity()`:

```python
score += min(max_velocity / VELOCITY_THRESHOLD * 40, 60)  # up to 60 pts for velocity
score += min(geo_flags * 10, 30)                          # up to 30 pts for geo flags
score += 10 if acc_txns["is_fraud"].any() else 0          # 10 pts for known fraud txns
risk_score = min(int(score), 100)
```

| Score / Signal | Risk Level |
|---|---|
| Score ≥ 60, OR velocity ≥ 15, OR geo flags ≥ 3 | 🔴 High |
| Score ≥ 25, OR velocity ≥ 5, OR any geo flag | 🟡 Medium |
| Score < 25 | 🟢 Low |

Velocity is computed using a rolling 5-minute window: for each transaction timestamp, count all transactions in the preceding 5 minutes. The maximum across all windows is `max_velocity`. The threshold is 5 transactions per window.

---

## Observability (Langfuse)

All agent runs are traced to a self-hosted Langfuse v2 instance.

### SDK Version

FraudGuard pins `langfuse>=2.0.0,<3.0.0`. The self-hosted Docker image (`langfuse/langfuse:2`) does not support the OTLP span export used by Langfuse v4 SDK — using v4 produces `404 Not Found` on every trace flush. The v2 SDK uses the stable low-level API.

### Tracing API

```python
trace  = langfuse.trace(name="fraud-agent-run", input=user_input,
                        session_id=session_id, user_id=analyst)
gen1   = trace.generation(name="data-agent", model=model_name, input=...)
gen1.end(output=data_output)
gt     = trace.span(name="ground-truth-verifier", input=data_output)
gt.end(output=ground_truth_report)
gen2   = trace.generation(name="audit-agent", model=model_name, input=...)
gen2.end(output=audit_output)
gen3   = trace.generation(name="synthesis-agent", model=model_name, input=...)
gen3.end(output=final_report)
trace.update(output=final_report)
langfuse.flush()
```

### What Gets Traced

Each investigation produces one parent trace with four children: `data-agent` (generation), `ground-truth-verifier` (span), `audit-agent` (generation), `synthesis-agent` (generation). Session ID and analyst name are attached to every trace.

### Dashboard Integration

The FraudGuard home page pulls recent trace activity from Langfuse via `lf.get_traces(limit=20, name="fraud-agent-run")` cached at `ttl=60` seconds. The last 5 runs are displayed with timestamp and session ID.

---

## UI Design

### Dark Navy Sidebar

The sidebar uses `#1e293b` background with `#94a3b8` body text. Streamlit's auto-generated page navigation is hidden:

```css
[data-testid="stSidebarNav"] { display: none !important; }
```

Navigation is replaced by a custom `render_sidebar_nav()` component in `components.py` using `st.page_link()`, giving consistent branding and ordering across all pages.

### Shared Sidebar Component

`components.py` exports `render_sidebar_nav()`. Every page calls it inside `with st.sidebar:`. It renders FraudGuard branding, navigation links to all 4 pages, and live agent status dots (Velocity, Invoice, Audit, Synthesis).

### Color Palette

| Usage | Value |
|---|---|
| Main background | `#eef2f8` |
| Sidebar | `#1e293b` |
| High risk card border | `#6e2929` |
| High risk card background | `#1c0d0d` |
| Medium risk card border | `#4d3608` |
| Risk score color (high) | `#f85149` |
| Risk score color (medium) | `#d29922` |

### Pipeline Progress Indicator

While an investigation runs, a visual step indicator shows which stage is active:

```
① Data Agent  →  ② Audit Agent  →  ③ Synthesis Agent
```

After completion, the Pipeline Debug expander shows the raw output of every stage plus the ground truth verification status.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| UI | Streamlit 1.35+ | Multi-page app, wide layout, `st.page_link` nav |
| Agent framework | LangGraph | `StateGraph` with `ToolNode`, conditional edges |
| LLM | `qwen2.5:14b` via Ollama | Local, `temperature=0` for determinism |
| LLM client | `langchain-ollama` `ChatOllama` | Tools bound for Data Agent stage |
| Observability | Langfuse v2 self-hosted | `langfuse/langfuse:2` Docker image |
| Langfuse SDK | `langfuse==2.*` | Pinned — v4 SDK incompatible with v2 server |
| Database | SQLite via `sqlite3` | Analyst decisions only, gitignored |
| Data | Pandas + synthetic CSVs | `transactions.csv`, `accounts.csv`, `invoices.csv` |
| Visualization | Plotly | Charts in account lookup and dashboard |
| Env management | `python-dotenv` | `.env` file, never committed |
| Python | 3.11+ | Virtual environment via `uv` |

---

## Setup

### Prerequisites

- Python 3.11+
- [Docker Desktop](https://www.docker.com/)
- [Ollama](https://ollama.com/)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/fraudguard.git
cd fraudguard
```

### 2. Create virtual environment and install dependencies

```bash
uv venv .venv
uv pip install -r requirements.txt
```

Or with standard pip:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Pull the model

```bash
ollama pull qwen2.5:14b
```

Downloads ~9GB. Only needed once.

### 4. Start Langfuse

```bash
docker compose up -d
```

Open [http://localhost:3000](http://localhost:3000), create an account, then go to **Settings → API Keys** and create a key pair.

### 5. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b

LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

### 6. Run the app

```bash
.venv/bin/streamlit run account_lookup.py
```

---

## Every Session

```bash
docker compose up -d                          # Langfuse + Postgres
ollama serve                                  # Ollama (if not already running)
.venv/bin/streamlit run account_lookup.py     # App
```

To stop:

```bash
docker compose down        # stops containers, keeps trace data
docker compose down -v     # also wipes Langfuse trace history (Postgres volume)
```

---

## Project Structure

```
financeagent/
├── account_lookup.py          # Dashboard + account lookup (Streamlit entry point)
├── agent.py                   # Velocity fraud 3-stage pipeline + ground truth verifier
├── invoice_agent.py           # Invoice fraud 3-stage pipeline
├── utils.py                   # Velocity computation, risk scoring, SQLite, invoice detectors
├── components.py              # Shared sidebar nav (render_sidebar_nav)
├── requirements.txt           # Pinned Python dependencies
├── docker-compose.yml         # Langfuse + Postgres
├── .env.example               # Environment variable template
├── .gitignore
│
├── css/
│   └── style.css              # Dark sidebar, card styles, pipeline indicator, badges
│
├── pages/
│   ├── alert_queue.py         # Alert Queue: ranked cards, block/clear/escalate/monitor
│   ├── 2_Agent_Chat.py        # Agent Chat: conversation, pipeline debug panel
│   └── 3_Invoice_Fraud.py     # Invoice Fraud: upload + agent analysis
│
├── synthetictables/
│   ├── transactions.csv       # Synthetic transaction data
│   ├── accounts.csv           # Synthetic account data
│   └── invoices.csv           # Synthetic invoice data
│
├── scripts/
│   └── generate_invoices.py   # Invoice data generator
│
└── tests/
    ├── test_utils.py
    └── test_invoice_agent.py
```

---

## Agent Tools Reference

### Velocity Fraud Tools (`agent.py`)

| Tool | Input | Returns |
|---|---|---|
| `lookup_account` | `account_id` | Name, type, home city, KYC status, dormancy, risk tier |
| `get_transaction_history` | `account_id`, `limit` | Recent transactions with velocity/geo flags and fraud type |
| `analyze_velocity` | `account_id` | Max velocity, threshold, risk score, risk level, geo flags, peak window, fraud types |
| `get_similar_flagged_accounts` | `account_id` | Other accounts with fraud activity overlapping in time or city |
| `record_decision` | `account_id`, `decision`, `notes` | Persists block/clear/escalate/monitor to SQLite |

### Invoice Fraud Tools (`invoice_agent.py`)

| Tool | Returns |
|---|---|
| `get_invoice_summary` | Total invoices, spend, vendor count, department breakdown |
| `find_duplicate_invoices` | Exact and near-duplicate invoice pairs with total financial exposure |
| `find_split_billing` | Vendor groups with suspicious invoice clustering |
| `find_threshold_avoidance` | Invoices between $9,500–$9,999.99 |
| `find_ghost_vendors` | Vendors appearing in fewer than 3 invoices total |

---

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | No | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen2.5:14b` | No | Model name passed to `ChatOllama` |
| `LANGFUSE_HOST` | `http://localhost:3000` | Yes | Self-hosted Langfuse URL |
| `LANGFUSE_PUBLIC_KEY` | — | Yes | From Langfuse Settings → API Keys |
| `LANGFUSE_SECRET_KEY` | — | Yes | From Langfuse Settings → API Keys |

---

## Notes

- `fraudguard.db` is gitignored — analyst decisions are local only
- Synthetic data in `synthetictables/` is safe to commit
- The Langfuse SDK is pinned to `<3.0.0` — do not upgrade without also upgrading the Docker image to `langfuse/langfuse:3`
- `qwen2.5:14b` is the minimum recommended model size for reliable structured output in the Audit and Synthesis stages; smaller models produce inconsistent formatting
