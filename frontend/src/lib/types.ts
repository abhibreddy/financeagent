// Types mirroring the FastAPI backend response shapes (backend/routers/*).

export type RiskLevel = "High" | "Medium" | "Low";

export interface Alert {
  account_id: string;
  customer: string;
  account_type: string;
  home_city: string;
  risk_level: RiskLevel;
  risk_score: number;
  max_velocity: number;
  geo_flags: number;
  total_amount: number;
  fraud_types: string;
  is_dormant: boolean;
  kyc_verified: boolean;
  peak_start: string | null;
  peak_end: string | null;
}

export interface Velocity {
  max_velocity: number;
  peak_window: [string | null, string | null];
  geo_flags: number;
  total_amount: number;
  fraud_types: string[];
  risk_level: RiskLevel;
  risk_score: number;
}

export interface AccountDetail {
  account: Record<string, unknown>;
  velocity: Velocity;
  transactions: Record<string, unknown>[];
}

export interface Decision {
  account_id: string;
  decision: string;
  analyst: string;
  notes: string;
  decided_at: string;
}

export interface InvoiceRecord {
  invoice_id: string;
  vendor: string;
  amount: number;
  date: string;
  department: string;
  category: string;
  approver: string;
  fraud_type: string;
  [k: string]: unknown;
}

export interface InvoiceReport {
  total_invoices: number;
  flagged_count: number;
  exact_duplicates: InvoiceRecord[];
  near_duplicates: InvoiceRecord[];
  split_billing: InvoiceRecord[];
  threshold_avoidance: InvoiceRecord[];
  ghost_vendors: InvoiceRecord[];
  total_flagged_amount: number;
}

export interface PortfolioReport {
  portfolio: {
    total_market_value: number;
    total_cost_basis: number;
    unrealized_pnl: number;
    unrealized_pnl_pct: number;
    num_positions: number;
    weights: Record<string, number>;
  };
  exposure: {
    sector_exposure: Record<string, number>;
    asset_class_exposure: Record<string, number>;
    largest_position: string;
    largest_weight_pct: number;
    concentration_level: RiskLevel;
  };
  risk: {
    portfolio_daily_volatility: number;
    annualized_volatility_pct: number;
    worst_drawdown_pct: number;
    risk_score: number;
    risk_level: RiskLevel;
  };
}

export interface Position {
  position_id: string;
  ticker: string;
  sector: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  asset_class: string;
}

export interface ForecastResult {
  symbol: string;
  as_of: string;
  prompt: string;
  report: string;
  engine?: "azure" | "fingpt";
  model?: string;
  latency_ms?: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

// Finance AI Suite (backend/routers/finance_suite.py)

export interface SuiteAgent {
  key: string;
  title: string;
  icon: string;
  subtitle: string;
  has_report: boolean;
  suggestions: string[];
}

export interface SuiteScenario {
  id: string;
  name: string;
  description: string;
}

export interface ApReport {
  total_outstanding: number;
  aging: { current: number; d1_30: number; d31_60: number; d60_plus: number };
  overdue_count: number;
  overdue_amount: number;
  early_pay_savings: number;
  duplicate_po_risk: number;
  bill_count: number;
}

export interface ArReport {
  total_receivable: number;
  overdue_amount: number;
  at_risk_amount: number;
  disputed_count: number;
  dso_days: number;
  dunning_priority: Record<string, number>;
  invoice_count: number;
}

export interface CashflowReport {
  opening_cash: number;
  total_inflow: number;
  total_outflow: number;
  ending_cash: number;
  min_cash: number;
  runway_weeks: number;
  cash_crunch: boolean;
  weeks_count: number;
}

export interface ReconciliationReport {
  total_items: number;
  matched: number;
  break_count: number;
  match_rate_pct: number;
  break_amount: number;
  breaks_by_type: Record<string, number>;
}

export interface InsightsReport {
  revenue: number;
  gross_margin_pct: number;
  net_margin_pct: number;
  opex_ratio_pct: number;
  revenue_growth_pct: number;
  budget_variance_pct: number;
}

export interface SuiteReportResponse<T> {
  agent: string;
  scenario: SuiteScenario;
  report: T;
}
