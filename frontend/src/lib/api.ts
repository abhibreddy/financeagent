// Typed client for the FastAPI backend.
import type {
  Alert, AccountDetail, Decision, InvoiceReport, PortfolioReport, Position, ForecastResult,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error((detail as { detail?: string }).detail ?? `POST ${path} → ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Finance
  alerts: () => get<{ threshold: number; alerts: Alert[] }>("/api/finance/alerts"),
  account: (id: string) => get<AccountDetail>(`/api/finance/accounts/${id}`),
  compare: (ids: string[]) =>
    post<{ comparison: Record<string, unknown>[] }>("/api/finance/accounts/compare", { account_ids: ids }),
  decisions: () => get<{ decisions: Record<string, Decision> }>("/api/finance/decisions"),
  saveDecision: (account_id: string, decision: string, analyst = "analyst", notes = "") =>
    post<{ ok: boolean; decisions: Record<string, Decision> }>("/api/finance/decisions", {
      account_id, decision, analyst, notes,
    }),
  invoicesReport: () => get<InvoiceReport>("/api/finance/invoices/report"),

  // Trading
  portfolio: () => get<{ report: PortfolioReport; positions: Position[] }>("/api/trading/portfolio"),
  prices: (ticker: string) =>
    get<{ ticker: string; prices: { date: string; close: number }[] }>(`/api/trading/prices/${ticker}`),
  forecast: (symbol: string, weeks: number, with_basics: boolean, engine: "azure" | "fingpt" = "azure") =>
    post<ForecastResult>("/api/trading/forecast", { symbol, weeks, with_basics, engine }),
};
