"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SuiteScenario, ApReport } from "@/lib/types";
import { usd } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { AgentChat } from "@/components/agent-chat";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScenarioSelect } from "@/components/scenario-select";
import { ErrorState } from "@/app/finance/dashboard/page";

const AGENT = "ap";
const AGING_LABELS: Record<string, string> = {
  current: "Current",
  d1_30: "1–30 days",
  d31_60: "31–60 days",
  d60_plus: "60+ days",
};

export default function AccountsPayable() {
  const [scenarios, setScenarios] = useState<SuiteScenario[]>([]);
  const [scenario, setScenario] = useState("");
  const [report, setReport] = useState<ApReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .suiteScenarios(AGENT)
      .then((d) => {
        setScenarios(d.scenarios);
        if (d.scenarios[0]) setScenario(d.scenarios[0].id);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!scenario) return;
    setReport(null);
    api
      .suiteReport<ApReport>(AGENT, scenario)
      .then((d) => setReport(d.report))
      .catch((e) => setError(String(e)));
  }, [scenario]);

  if (error) return <ErrorState error={error} />;

  return (
    <div>
      <PageHeader title="Accounts Payable" subtitle="Payables aging, overdue exposure & early-pay savings" />

      <ScenarioSelect scenarios={scenarios} value={scenario} onChange={setScenario} />

      {report && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total Outstanding" value={usd(report.total_outstanding)} />
            <StatCard
              label="Overdue Amount"
              value={usd(report.overdue_amount)}
              tone={report.overdue_amount ? "danger" : "default"}
              hint={`${report.overdue_count} overdue bills`}
            />
            <StatCard label="Early-Pay Savings" value={usd(report.early_pay_savings)} />
            <StatCard
              label="Duplicate PO Risk"
              value={report.duplicate_po_risk}
              tone={report.duplicate_po_risk ? "warning" : "default"}
              hint={`${report.bill_count} bills`}
            />
          </div>

          <Card className="mt-6 p-5">
            <div className="mb-3 text-sm font-semibold">Aging Breakdown</div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Bucket</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(report.aging).map(([bucket, amount]) => (
                  <TableRow key={bucket}>
                    <TableCell>{AGING_LABELS[bucket] ?? bucket}</TableCell>
                    <TableCell className="text-right tabular-nums">{usd(amount)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </>
      )}

      <div className="mt-8 border-t border-border pt-6">
        <AgentChat
          endpoint={`/api/agents/suite/${AGENT}/stream`}
          scenario={scenario}
          title="Payables Copilot"
          subtitle="Ask about overdue bills, payment timing & duplicate risk"
          avatar="📤"
          suggestions={[
            "Which bills should I pay this week?",
            "Where can I capture early-pay discounts?",
            "Any duplicate PO risk to flag?",
          ]}
        />
      </div>
    </div>
  );
}
