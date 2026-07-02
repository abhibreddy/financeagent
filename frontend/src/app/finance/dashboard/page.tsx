"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Alert } from "@/lib/types";
import { usd, riskVariant } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function FinanceDashboard() {
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.alerts().then((d) => setAlerts(d.alerts)).catch((e) => setError(String(e)));
  }, []);

  if (error) return <ErrorState error={error} />;
  if (!alerts) return <LoadingState />;

  const high = alerts.filter((a) => a.risk_level === "High").length;
  const medium = alerts.filter((a) => a.risk_level === "Medium").length;
  const low = alerts.filter((a) => a.risk_level === "Low").length;
  const avg = alerts.length ? Math.round(alerts.reduce((s, a) => s + a.risk_score, 0) / alerts.length) : 0;
  const flaggedAmount = alerts.reduce((s, a) => s + (a.total_amount || 0), 0);

  return (
    <div>
      <PageHeader title="Fraud Dashboard" subtitle="Velocity & geo-anomaly risk monitoring" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Flagged Accounts" value={alerts.length} />
        <StatCard label="High Risk" value={high} tone={high ? "danger" : "default"} hint="immediate action" />
        <StatCard label="Avg Risk Score" value={avg} />
        <StatCard label="Flagged Amount" value={usd(flaggedAmount)} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="p-5">
          <div className="text-sm font-semibold">Risk Distribution</div>
          <div className="mt-4 space-y-3">
            {[
              { label: "High", n: high, cls: "bg-destructive" },
              { label: "Medium", n: medium, cls: "bg-amber-500" },
              { label: "Low", n: low, cls: "bg-emerald-500" },
            ].map((r) => (
              <div key={r.label}>
                <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                  <span>{r.label} Risk</span>
                  <span>{r.n}</span>
                </div>
                <div className="h-2 w-full rounded-full bg-muted">
                  <div
                    className={`h-2 rounded-full ${r.cls}`}
                    style={{ width: `${alerts.length ? (r.n / alerts.length) * 100 : 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">Recent High-Risk Events</div>
            <Link href="/finance/alerts" className="text-xs text-primary hover:underline">
              View all →
            </Link>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Account</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Risk</TableHead>
                <TableHead>Max Vel</TableHead>
                <TableHead>Geo</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alerts.slice(0, 8).map((a) => (
                <TableRow key={a.account_id}>
                  <TableCell>
                    <Link href={`/finance/accounts/${a.account_id}`} className="font-medium text-primary hover:underline">
                      {a.account_id}
                    </Link>
                  </TableCell>
                  <TableCell>{a.customer}</TableCell>
                  <TableCell>
                    <Badge variant={riskVariant(a.risk_level)}>{a.risk_score}</Badge>
                  </TableCell>
                  <TableCell className="tabular-nums">{a.max_velocity}</TableCell>
                  <TableCell className="tabular-nums">{a.geo_flags}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}

export function LoadingState() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-48" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}

export function ErrorState({ error }: { error: string }) {
  return (
    <Card className="border-destructive/30 bg-destructive/5 p-6">
      <div className="font-semibold text-destructive">Couldn&apos;t reach the API</div>
      <p className="mt-1 text-sm text-muted-foreground">{error}</p>
      <p className="mt-2 text-xs text-muted-foreground">
        Is the backend running? <code className="rounded bg-muted px-1">uvicorn backend.main:app --port 8000</code>
      </p>
    </Card>
  );
}
