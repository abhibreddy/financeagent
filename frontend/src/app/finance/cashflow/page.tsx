"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SuiteScenario, CashflowReport } from "@/lib/types";
import { usd } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { AgentChat } from "@/components/agent-chat";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScenarioSelect } from "@/components/scenario-select";
import { ErrorState } from "@/app/finance/dashboard/page";

const AGENT = "cashflow";

export default function CashFlow() {
  const [scenarios, setScenarios] = useState<SuiteScenario[]>([]);
  const [scenario, setScenario] = useState("");
  const [report, setReport] = useState<CashflowReport | null>(null);
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
      .suiteReport<CashflowReport>(AGENT, scenario)
      .then((d) => setReport(d.report))
      .catch((e) => setError(String(e)));
  }, [scenario]);

  if (error) return <ErrorState error={error} />;

  return (
    <div>
      <PageHeader title="Cash Flow" subtitle="Liquidity forecast, runway & cash-crunch detection" />

      <ScenarioSelect scenarios={scenarios} value={scenario} onChange={setScenario} />

      {report && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Opening Cash" value={usd(report.opening_cash)} />
            <StatCard label="Ending Cash" value={usd(report.ending_cash)} hint={`over ${report.weeks_count} weeks`} />
            <StatCard
              label="Min Cash"
              value={usd(report.min_cash)}
              tone={report.cash_crunch ? "danger" : "default"}
            />
            <StatCard
              label="Runway"
              value={`${report.runway_weeks} wks`}
              tone={report.cash_crunch ? "danger" : "default"}
              hint={report.cash_crunch ? "cash crunch ahead" : "healthy"}
            />
          </div>

          <Card className="mt-6 p-5">
            <div className="mb-3 text-sm font-semibold">Flow Summary</div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Line</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell>Total Inflow</TableCell>
                  <TableCell className="text-right tabular-nums">{usd(report.total_inflow)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Total Outflow</TableCell>
                  <TableCell className="text-right tabular-nums">{usd(report.total_outflow)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Net Change</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {usd(report.total_inflow - report.total_outflow)}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Card>
        </>
      )}

      <div className="mt-8 border-t border-border pt-6">
        <AgentChat
          endpoint={`/api/agents/suite/${AGENT}/stream`}
          scenario={scenario}
          title="Cash Flow Copilot"
          subtitle="Ask about runway, upcoming crunches & liquidity levers"
          avatar="💧"
          suggestions={[
            "When do we risk running out of cash?",
            "How can we extend runway?",
            "Break down inflows vs outflows.",
          ]}
        />
      </div>
    </div>
  );
}
