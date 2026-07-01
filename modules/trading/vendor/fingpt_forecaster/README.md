# Vendored: FinGPT-Forecaster (attribution)

These files are copied verbatim from
[AI4Finance-Foundation/FinGPT](https://github.com/AI4Finance-Foundation/FinGPT),
`fingpt/FinGPT_Forecaster/`, and are included **for reference and attribution only**.

- `prompt.py` — FinGPT-Forecaster's prompt construction (company intro, weekly news +
  price movement, basic financials, prediction ending).
- `app.py` — the original Gradio demo that loads Llama-2-7b + a LoRA adapter locally.
- `LICENSE` — FinGPT's MIT license.

## How this project uses it

The Trading module does **not** run FinGPT's fine-tuned Llama model (that needs ~13 GB of
weights and a GPU). Instead, `modules/trading/forecaster.py` re-implements FinGPT-Forecaster's
**methodology** — the same system prompt and company/news/financials prompt structure — and
runs the reasoning through this project's existing **Azure OpenAI** model. Market data is
pulled from Finnhub + yfinance (see `prompt.py` for the original data pipeline).

Original methodology and prompts © AI4Finance Foundation, MIT License.
