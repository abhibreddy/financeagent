"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AccountDetail } from "@/lib/types";
import { usd2, riskVariant } from "@/lib/format";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { LoadingState, ErrorState } from "../../dashboard/page";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const VELOCITY_THRESHOLD = 5; // matches modules/finance/utils.py

function InfoRow({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between border-b border-border py-2 text-sm last:border-0">
      <span className="text-muted-foreground">{k}</span>
      <span className="font-medium">{v}</span>
    </div>
  );
}

/** Reconstruct the risk-score drivers using the same weighting as compute_velocity(). */
function riskDrivers(v: AccountDetail["velocity"]) {
  const velPts = Math.min(Math.round((v.max_velocity / VELOCITY_THRESHOLD) * 40), 60);
  const geoPts = Math.min(v.geo_flags * 10, 30);
  const fraudPts = v.fraud_types.length ? 10 : 0;
  const drivers = [
    {
      key: "velocity",
      active: v.max_velocity >= VELOCITY_THRESHOLD,
      points: velPts,
      label: "Transaction velocity",
      detail: `${v.max_velocity} transactions in a 5-min window (threshold ${VELOCITY_THRESHOLD})`,
    },
    {
      key: "geo",
      active: v.geo_flags > 0,
      points: geoPts,
      label: "Geo anomalies",
      detail: `${v.geo_flags} transaction${v.geo_flags === 1 ? "" : "s"} flagged in an unexpected location`,
    },
    {
      key: "fraud",
      active: fraudPts > 0,
      points: fraudPts,
      label: "Known fraud patterns",
      detail: v.fraud_types.length ? v.fraud_types.join(", ") : "none",
    },
  ].filter((d) => d.active);
  const dominant = drivers.slice().sort((a, b) => b.points - a.points)[0];
  return { drivers, dominant };
}

export default function AccountDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [data, setData] = useState<AccountDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.account(id).then(setData).catch((e) => setError(String(e)));
  }, [id]);

  if (error) return <ErrorState error={error} />;
  if (!data) return <LoadingState />;

  const acc = data.account as Record<string, unknown>;
  const v = data.velocity;
  const txns = data.transactions.slice(0, 20);
  const flaggedCount = data.transactions.filter((t) => t.velocity_flag || t.geo_flag).length;
  const { drivers, dominant } = riskDrivers(v);
  const showWhy = v.risk_level !== "Low" && drivers.length > 0;
  const [peakStart, peakEnd] = v.peak_window;

  return (
    <div>
      <Link href="/finance/alerts" className="text-sm text-primary hover:underline">
        ← Back to Alert Queue
      </Link>
      <PageHeader title={String(acc.account_id ?? id)} subtitle={String(acc.customer_name ?? "")} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Max Txns / 5min" value={v.max_velocity} tone={v.max_velocity >= VELOCITY_THRESHOLD ? "danger" : "default"} />
        <StatCard label="Risk Score" value={`${v.risk_score}/100`} tone={v.risk_level === "High" ? "danger" : v.risk_level === "Medium" ? "warning" : "default"} />
        <StatCard label="Geo Flags" value={v.geo_flags} tone={v.geo_flags ? "warning" : "default"} />
        <StatCard label="Total Amount" value={usd2(v.total_amount)} />
      </div>

      {/* Why this account is flagged — risk-driver breakdown */}
      {showWhy && (
        <Card
          className={cn(
            "mt-6 border-l-4 p-5",
            v.risk_level === "High" ? "border-l-destructive bg-destructive/5" : "border-l-amber-500 bg-amber-500/5"
          )}
        >
          <div className="mb-2 flex items-center gap-2">
            <Badge variant={riskVariant(v.risk_level)}>{v.risk_level} Risk</Badge>
            <span className="text-sm font-semibold">Why this account is flagged</span>
          </div>
          <p className="text-sm text-muted-foreground">
            Scored <span className="font-semibold text-foreground">{v.risk_score}/100</span>, primarily driven by{" "}
            <span className="font-semibold text-foreground">{dominant.label.toLowerCase()}</span>
            {peakStart && (
              <> · peak window {String(peakStart).slice(0, 16).replace("T", " ")} → {String(peakEnd).slice(11, 16)}</>
            )}
            .
          </p>
          <ul className="mt-3 space-y-2">
            {drivers.map((d) => (
              <li key={d.key} className="flex items-start justify-between gap-4 rounded-md border border-border bg-card p-3 text-sm">
                <div>
                  <div className="font-semibold">{d.label}</div>
                  <div className="text-muted-foreground">{d.detail}</div>
                </div>
                <Badge variant={d.key === "velocity" ? "danger" : d.key === "geo" ? "warning" : "destructive"}>
                  +{d.points} pts
                </Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-sm font-semibold">Account Info</div>
            <Badge variant={riskVariant(v.risk_level)}>{v.risk_level} Risk</Badge>
          </div>
          <InfoRow k="Account Type" v={String(acc.account_type ?? "—")} />
          <InfoRow k="Home City" v={String(acc.home_city ?? "—")} />
          <InfoRow k="Risk Tier" v={String(acc.risk_tier ?? "—")} />
          <InfoRow k="KYC Verified" v={acc.kyc_verified ? "✓ Yes" : "✗ No"} />
          <InfoRow k="Dormant" v={acc.is_dormant ? `Yes (${acc.dormant_days} days)` : "No"} />
          <InfoRow k="Fraud Types" v={v.fraud_types.length ? v.fraud_types.join(", ") : "None"} />
        </Card>

        <Card className="p-5">
          <div className="mb-1 flex items-center justify-between">
            <div className="text-sm font-semibold">Recent Transactions</div>
            {flaggedCount > 0 && (
              <span className="text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">{flaggedCount}</span> flagged
              </span>
            )}
          </div>
          <p className="mb-3 text-xs text-muted-foreground">Bold rows are flagged transactions driving the risk score.</p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>City</TableHead>
                <TableHead>Flags</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {txns.map((t, i) => {
                const flagged = Boolean(t.velocity_flag || t.geo_flag);
                return (
                  <TableRow key={i} className={cn(flagged && "bg-destructive/5 font-semibold")}>
                    <TableCell className="whitespace-nowrap text-xs">{String(t.timestamp).slice(0, 16).replace("T", " ")}</TableCell>
                    <TableCell className="tabular-nums">{usd2(Number(t.amount))}</TableCell>
                    <TableCell>{String(t.city ?? "—")}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {t.velocity_flag ? <Badge variant="danger">VELOCITY</Badge> : null}
                        {t.geo_flag ? <Badge variant="warning">GEO</Badge> : null}
                        {!flagged ? <span className="text-xs text-muted-foreground">OK</span> : null}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}
