import type { RiskLevel } from "./types";

export const usd = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export const usd2 = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

export const pct = (n: number | null | undefined) => (n == null ? "—" : `${n.toFixed(2)}%`);

export const riskVariant = (level: RiskLevel): "danger" | "warning" | "success" =>
  level === "High" ? "danger" : level === "Medium" ? "warning" : "success";
