"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { ForecastResult } from "@/lib/types";
import { Markdown } from "@/components/markdown";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Engine = "azure" | "fingpt";

const ENGINES: { id: Engine; label: string; blurb: string }[] = [
  { id: "azure", label: "Azure OpenAI", blurb: "FinGPT methodology on gpt-4o-mini · fast & reliable" },
  { id: "fingpt", label: "FinGPT (local)", blurb: "Actual fine-tuned Llama-2 model via Ollama · ~10–30s" },
];

export default function StockForecaster() {
  const [symbol, setSymbol] = useState("AAPL");
  const [weeks, setWeeks] = useState(2);
  const [withBasics, setWithBasics] = useState(true);
  const [engine, setEngine] = useState<Engine>("fingpt");
  const [result, setResult] = useState<ForecastResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!symbol.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.forecast(symbol.trim().toUpperCase(), weeks, withBasics, engine));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <PageHeader title="Stock Forecaster" subtitle="FinGPT-Forecaster · Azure reimplementation or the real local model" />

      {/* Engine selector */}
      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        {ENGINES.map((e) => (
          <button
            key={e.id}
            onClick={() => setEngine(e.id)}
            className={cn(
              "rounded-lg border p-3 text-left transition-colors",
              engine === e.id ? "border-primary bg-accent" : "border-border hover:bg-accent/50"
            )}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">{e.label}</span>
              {engine === e.id && <Badge>selected</Badge>}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">{e.blurb}</div>
          </button>
        ))}
      </div>

      <p className="mb-4 text-xs text-muted-foreground">
        Market data via Finnhub + yfinance (needs FINNHUB_API_KEY on the backend). FinGPT engine runs the
        actual fine-tuned model locally through Ollama + the host FinGPT service.
      </p>

      <Card className="p-5">
        <div className="grid gap-4 sm:grid-cols-[2fr_1fr_1fr]">
          <div>
            <label className="mb-1 block text-sm font-medium">Ticker</label>
            <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="AAPL" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Past weeks: {weeks}</label>
            <input
              type="range"
              min={1}
              max={engine === "fingpt" ? 3 : 4}
              value={Math.min(weeks, engine === "fingpt" ? 3 : 4)}
              onChange={(e) => setWeeks(Number(e.target.value))}
              className="mt-2 w-full accent-primary"
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={withBasics} onChange={(e) => setWithBasics(e.target.checked)} />
              Include financials
            </label>
          </div>
        </div>
        <Button className="mt-4" onClick={run} disabled={loading}>
          {loading ? (engine === "fingpt" ? "Running FinGPT locally… (~10–30s)" : "Forecasting…") : "🔮 Generate Forecast"}
        </Button>
      </Card>

      {loading && (
        <Card className="mt-4 flex items-center gap-3 p-4 text-sm text-muted-foreground">
          <span className="inline-block size-2 animate-pulse rounded-full bg-primary" />
          {engine === "fingpt"
            ? "The local FinGPT-Forecaster model is generating — first run after startup can take longer."
            : "Gathering market data and forecasting…"}
        </Card>
      )}

      {error && (
        <Card className="mt-4 border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {error}
          {engine === "fingpt" && (
            <div className="mt-2 text-xs text-muted-foreground">
              Is Ollama + the FinGPT service running? You can switch to the Azure engine above.
            </div>
          )}
        </Card>
      )}

      {result && (
        <Card className="mt-6 p-6">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {result.symbol} — outlook as of {result.as_of}
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={result.engine === "fingpt" ? "default" : "secondary"}>
                {result.engine === "fingpt" ? `FinGPT · ${result.model}` : "Azure OpenAI"}
              </Badge>
              {result.latency_ms != null && (
                <span className="text-xs text-muted-foreground">{(result.latency_ms / 1000).toFixed(1)}s</span>
              )}
            </div>
          </div>
          <Markdown>{result.report}</Markdown>
          <details className="mt-4 text-xs">
            <summary className="cursor-pointer text-muted-foreground">Prompt sent to the model</summary>
            <pre className="mt-2 whitespace-pre-wrap rounded bg-muted p-3">{result.prompt}</pre>
          </details>
        </Card>
      )}
    </div>
  );
}
