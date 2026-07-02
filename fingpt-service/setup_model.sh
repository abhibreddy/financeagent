#!/usr/bin/env bash
# setup_model.sh — one-time (idempotent) FinGPT-Forecaster setup in Ollama.
#   1. ensure Ollama is running
#   2. pull the ungated pre-merged GGUF (6.67 GB, already quantized — imported as-is)
#   3. create the `fingpt-forecaster` model (Llama-2 template + FinGPT system prompt, num_ctx 4096)
#   4. warm it up so the first real request isn't a cold 7B load
set -euo pipefail
cd "$(dirname "$0")"

BASE="hf.co/Joshua265/fingpt-forecaster_llama2-7b-gguf"
MODEL="fingpt-forecaster"

echo "→ Checking Ollama…"
if ! ollama list >/dev/null 2>&1; then
  echo "  starting ollama serve in the background…"
  (ollama serve >/tmp/ollama.log 2>&1 &)
  sleep 4
fi

echo "→ Pulling base GGUF ($BASE)… (skipped if cached)"
ollama pull "$BASE"

echo "→ Creating model '$MODEL' from Modelfile…"
ollama create "$MODEL" -f Modelfile

echo "→ Warmup (loads the 7B model so the first demo request is fast)…"
ollama run "$MODEL" "Reply with OK." >/dev/null 2>&1 || true

echo "✓ Done. Verify:  ollama list | grep $MODEL"
