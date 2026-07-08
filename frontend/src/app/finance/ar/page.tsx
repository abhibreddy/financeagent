"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SuiteScenario, ArReport } from "@/lib/types";
import { usd } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { AgentChat } from "@/components/agent-chat";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScenarioSelect } from "@/components/scenario-select";
import { ErrorState } from "@/app/finance/dashboard/page";

const AGENT = "ar";

export default function AccountsReceivable() {
  const [scenarios, setScenarios] = useState<SuiteScenario[]>([]);
  const [scenario, setScenario] = useState("");
  const [report, setReport] = useState<ArReport | null>(null);
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
      .suiteReport<ArReport>(AGENT, scenario)
      .then((d) => setReport(d.report))
      .catch((e) => setError(String(e)));
  }, [scenario]);

  if (error) return <ErrorState error={error} />;

  const dunning = report ? Object.entries(report.dunning_priority) : [];

  return (
    <div>
      <PageHeader title="Accounts Receivable" subtitle="Collections risk, DSO & dunning prioritization" />

      <ScenarioSelect scenarios={scenarios} value={scenario} onChange={setScenario} />

      {report && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total Receivable" value={usd(report.total_receivable)} hint={`${report.invoice_count} invoices`} />
            <StatCard
              label="Overdue Amount"
              value={usd(report.overdue_amount)}
              tone={report.overdue_amount ? "danger" : "default"}
            />
            <StatCard
              label="At-Risk Amount"
              value={usd(report.at_risk_amount)}
              tone={report.at_risk_amount ? "warning" : "default"}
              hint={`${report.disputed_count} disputed`}
            />
            <StatCard label="DSO" value={`${report.dso_days} days`} />
          </div>

          <Card className="mt-6 p-5">
            <div className="mb-3 text-sm font-semibold">Dunning Priority</div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Customer</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dunning.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={2} className="text-muted-foreground">
                      No customers flagged.
                    </TableCell>
                  </TableRow>
                ) : (
                  dunning.map(([customer, amount]) => (
                    <TableRow key={customer}>
                      <TableCell>{customer}</TableCell>
                      <TableCell className="text-right tabular-nums">{usd(amount)}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </>
      )}

      <div className="mt-8 border-t border-border pt-6">
        <AgentChat
          endpoint={`/api/agents/suite/${AGENT}/stream`}
          scenario={scenario}
          title="Collections Copilot"
          subtitle="Ask about overdue customers, disputes & collection strategy"
          avatar="📥"
          suggestions={[
            "Which customers should I chase first?",
            "What's driving our DSO?",
            "Summarize disputed invoices.",
          ]}
        />
      </div>
    </div>
  );
}
