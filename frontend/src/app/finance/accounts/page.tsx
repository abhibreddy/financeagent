"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Alert } from "@/lib/types";
import { usd, riskVariant } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { LoadingState, ErrorState } from "../dashboard/page";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

export default function AccountLookup() {
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    api.alerts().then((d) => setAlerts(d.alerts)).catch((e) => setError(String(e)));
  }, []);

  const filtered = useMemo(() => {
    if (!alerts) return [];
    const s = q.trim().toLowerCase();
    if (!s) return alerts;
    return alerts.filter((a) => a.account_id.toLowerCase().includes(s) || a.customer.toLowerCase().includes(s));
  }, [alerts, q]);

  if (error) return <ErrorState error={error} />;
  if (!alerts) return <LoadingState />;

  return (
    <div>
      <PageHeader title="Account Lookup" subtitle="Search flagged accounts and open a full risk profile" />
      <Input
        placeholder="Search by account ID or customer…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="mb-6 max-w-md"
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((a) => (
          <Link key={a.account_id} href={`/finance/accounts/${a.account_id}`}>
            <Card className="p-5 transition-all hover:-translate-y-0.5 hover:shadow-md">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold">{a.account_id}</div>
                  <div className="text-sm text-muted-foreground">
                    {a.customer} · {a.home_city}
                  </div>
                </div>
                <Badge variant={riskVariant(a.risk_level)}>{a.risk_score}</Badge>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                <div>
                  <div className="font-semibold tabular-nums">{a.max_velocity}</div>
                  <div className="text-muted-foreground">Max Vel</div>
                </div>
                <div>
                  <div className="font-semibold tabular-nums">{a.geo_flags}</div>
                  <div className="text-muted-foreground">Geo Flags</div>
                </div>
                <div>
                  <div className="font-semibold tabular-nums">{usd(a.total_amount)}</div>
                  <div className="text-muted-foreground">Amount</div>
                </div>
              </div>
            </Card>
          </Link>
        ))}
        {filtered.length === 0 && <p className="text-sm text-muted-foreground">No matching accounts.</p>}
      </div>
    </div>
  );
}
