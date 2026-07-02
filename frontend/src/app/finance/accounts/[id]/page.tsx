"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AccountDetail } from "@/lib/types";
import { usd2, riskVariant } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { LoadingState, ErrorState } from "../../dashboard/page";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function InfoRow({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between border-b border-border py-2 text-sm last:border-0">
      <span className="text-muted-foreground">{k}</span>
      <span className="font-medium">{v}</span>
    </div>
  );
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
  const txns = data.transactions.slice(0, 15);

  return (
    <div>
      <Link href="/finance/alerts" className="text-sm text-primary hover:underline">
        ← Back to Alert Queue
      </Link>
      <PageHeader title={String(acc.account_id ?? id)} subtitle={String(acc.customer_name ?? "")} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Max Txns / 5min" value={v.max_velocity} tone={v.max_velocity >= 5 ? "danger" : "default"} />
        <StatCard label="Risk Score" value={`${v.risk_score}/100`} tone={v.risk_level === "High" ? "danger" : "default"} />
        <StatCard label="Geo Flags" value={v.geo_flags} tone={v.geo_flags ? "warning" : "default"} />
        <StatCard label="Total Amount" value={usd2(v.total_amount)} />
      </div>

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
          <div className="mb-3 text-sm font-semibold">Recent Transactions</div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>City</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {txns.map((t, i) => (
                <TableRow key={i}>
                  <TableCell className="whitespace-nowrap text-xs">{String(t.timestamp).slice(0, 16).replace("T", " ")}</TableCell>
                  <TableCell className="tabular-nums">{usd2(Number(t.amount))}</TableCell>
                  <TableCell>{String(t.city ?? "—")}</TableCell>
                  <TableCell>{String(t.status ?? "—")}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}
