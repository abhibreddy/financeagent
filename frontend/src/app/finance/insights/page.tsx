"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SuiteScenario, InsightsReport } from "@/lib/types";
import { usd, pct } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { AgentChat } from "@/components/agent-chat";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScenarioSelect } from "@/components/scenario-select";
import { ErrorState } from "@/app/finance/dashboard/page";

const AGENT = "insights";

export default function FinancialInsights() {
  const [scenarios, setScenarios] = useState<SuiteScenario[]>([]);
  const [scenario, setScenario] = useState("");
  const [report, setReport] = useState<InsightsReport | null>(null);
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
      .suiteReport<InsightsReport>(AGENT, scenario)
      .then((d) => setReport(d.report))
      .catch((e) => setError(String(e)));
  }, [scenario]);

  if (error) return <ErrorState error={error} />;

  return (
    <div>
      <PageHeader title="Financial Insights" subtitle="Margins, growth & budget variance" />

      <ScenarioSelect scenarios={scenarios} value={scenario} onChange={setScenario} />

      {report && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Revenue" value={usd(report.revenue)} />
            <StatCard
              label="Revenue Growth"
              value={pct(report.revenue_growth_pct)}
              tone={report.revenue_growth_pct < 0 ? "danger" : "default"}
            />
            <StatCard label="Gross Margin" value={pct(report.gross_margin_pct)} />
            <StatCard
              label="Net Margin"
              value={pct(report.net_margin_pct)}
              tone={report.net_margin_pct < 0 ? "danger" : "default"}
            />
          </div>

          <Card className="mt-6 p-5">
            <div className="mb-3 text-sm font-semibold">Ratios</div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Metric</TableHead>
                  <TableHead className="text-right">Value</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell>Gross Margin</TableCell>
                  <TableCell className="text-right tabular-nums">{pct(report.gross_margin_pct)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Net Margin</TableCell>
                  <TableCell className="text-right tabular-nums">{pct(report.net_margin_pct)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Opex Ratio</TableCell>
                  <TableCell className="text-right tabular-nums">{pct(report.opex_ratio_pct)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Budget Variance</TableCell>
                  <TableCell className="text-right tabular-nums">{pct(report.budget_variance_pct)}</TableCell>
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
          title="Insights Copilot"
          subtitle="Ask about margins, growth drivers & budget variance"
          avatar="📊"
          suggestions={[
            "What's driving our margin trend?",
            "Explain the budget variance.",
            "How is revenue growth tracking?",
          ]}
        />
      </div>
    </div>
  );
}
