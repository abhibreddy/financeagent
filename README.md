# 🛡️ FraudGuard

A fraud detection dashboard and AI agent for investigating transaction velocity anomalies. Built with Streamlit, LangGraph, Ollama, and Langfuse.

---

## Features

- **Alert Queue** — ranked list of flagged accounts by risk score, with one-click block/clear/escalate/monitor decisions
- **Account Lookup** — deep-dive view of any account: velocity metrics, geo flags, dormancy signals, transaction timeline
- **Agent Chat** — conversational fraud investigation powered by a LangGraph agent running locally via Ollama
- **Observability** — all agent runs traced to a self-hosted Langfuse v2 instance (latency, token usage, session history)

---

## Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| Agent framework | LangGraph |
| LLM | Ollama (`qwen3.5`) |
| Observability | Langfuse v2 (self-hosted) |
| Database | SQLite (alert decisions) |
| Data | Pandas + synthetic CSV tables |

---

## Setup

### Prerequisites

- Python 3.11+
- [Docker](https://www.docker.com/)
- [Ollama](https://ollama.com/)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/fraudguard.git
cd fraudguard
```

### 2. Install Python dependencies

```bash
pip install streamlit pandas langchain-ollama langgraph langfuse python-dotenv
```

### 3. Configure environment

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5

LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

### 4. Start Langfuse (self-hosted)

```bash
docker compose up -d
```

Then open [http://localhost:3000](http://localhost:3000), create an account, and copy your API keys into `.env`.

### 5. Pull the Ollama model

```bash
ollama pull qwen2.5
```

### 6. Run the app

```bash
streamlit run account_lookup.py
```

---

## Every Session

```bash
docker compose up -d   # start Langfuse + Postgres
ollama serve           # start Ollama (if not already running)
streamlit run account_lookup.py
```

To stop:

```bash
docker compose down    # stops containers, keeps your data
```

---

## Risk Scoring

Accounts are scored 0–100 using a weighted combination of signals:

| Signal | Max points |
|---|---|
| Transaction velocity (txns / 5-min window) | 60 |
| Geographic anomaly flags | 30 |
| Known fraud transactions present | 10 |

| Score | Risk level |
|---|---|
| ≥ 60, or velocity ≥ 15, or geo flags ≥ 3 | 🔴 High |
| ≥ 25, or velocity ≥ 5, or any geo flag | 🟡 Medium |
| < 25 | 🟢 Low |

---

## Agent Tools

The LangGraph agent has access to five tools:

- `lookup_account` — account details, KYC status, dormancy
- `get_transaction_history` — recent transactions with flags
- `analyze_velocity` — velocity metrics and risk score
- `get_similar_flagged_accounts` — coordinated attack detection
- `record_decision` — persist block/clear/escalate/monitor decisions to SQLite

---

## Notes

- `fraudguard.db` is excluded from git — analyst decisions are local only
- Synthetic data in `synthetictables/` is safe to commit
- Langfuse traces are stored in the Docker Postgres volume and persist across restarts; only `docker compose down -v` will wipe them
