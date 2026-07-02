"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Alert, Decision } from "@/lib/types";
import { usd, riskVariant } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { LoadingState, ErrorState } from "../dashboard/page";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const ACTIONS: { decision: string; label: string; variant: "destructive" | "outline" | "secondary" }[] = [
  { decision: "blocked", label: "Block", variant: "destructive" },
  { decision: "cleared", label: "Clear", variant: "outline" },
  { decision: "escalated", label: "Escalate", variant: "secondary" },
  { decision: "monitoring", label: "Monitor", variant: "outline" },
];

const DECISION_BADGE: Record<string, "danger" | "success" | "warning" | "secondary"> = {
  blocked: "danger",
  cleared: "success",
  escalated: "warning",
  monitoring: "secondary",
};

export default function AlertQueue() {
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([api.alerts(), api.decisions()])
      .then(([a, d]) => {
        setAlerts(a.alerts);
        setDecisions(d.decisions);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => load(), [load]);

  async function act(accountId: string, decision: string) {
    setBusy(accountId + decision);
    try {
      const res = await api.saveDecision(accountId, decision, "analyst", "");
      setDecisions(res.decisions);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  if (error) return <ErrorState error={error} />;
  if (!alerts) return <LoadingState />;

  return (
    <div>
      <PageHeader title="Alert Queue" subtitle={`${alerts.length} flagged accounts ranked by risk`} />
      <Card className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Account</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Risk</TableHead>
              <TableHead>Amount</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {alerts.map((a) => {
              const d = decisions[a.account_id];
              return (
                <TableRow key={a.account_id}>
                  <TableCell>
                    <Link href={`/finance/accounts/${a.account_id}`} className="font-medium text-primary hover:underline">
                      {a.account_id}
                    </Link>
                  </TableCell>
                  <TableCell>{a.customer}</TableCell>
                  <TableCell>
                    <Badge variant={riskVariant(a.risk_level)}>
                      {a.risk_level} · {a.risk_score}
                    </Badge>
                  </TableCell>
                  <TableCell className="tabular-nums">{usd(a.total_amount)}</TableCell>
                  <TableCell>
                    {d ? (
                      <Badge variant={DECISION_BADGE[d.decision] ?? "secondary"}>{d.decision}</Badge>
                    ) : (
                      <span className="text-xs text-muted-foreground">Pending</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-1">
                      {ACTIONS.map((ac) => (
                        <Button
                          key={ac.decision}
                          size="sm"
                          variant={ac.variant}
                          disabled={busy !== null}
                          onClick={() => act(a.account_id, ac.decision)}
                        >
                          {busy === a.account_id + ac.decision ? "…" : ac.label}
                        </Button>
                      ))}
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
