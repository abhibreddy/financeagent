"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SuiteScenario, ReconciliationReport } from "@/lib/types";
import { usd, pct } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { AgentChat } from "@/components/agent-chat";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScenarioSelect } from "@/components/scenario-select";
import { ErrorState } from "@/app/finance/dashboard/page";

const AGENT = "reconciliation";

export default function Reconciliation() {
  const [scenarios, setScenarios] = useState<SuiteScenario[]>([]);
  const [scenario, setScenario] = useState("");
  const [report, setReport] = useState<ReconciliationReport | null>(null);
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
      .suiteReport<ReconciliationReport>(AGENT, scenario)
      .then((d) => setReport(d.report))
      .catch((e) => setError(String(e)));
  }, [scenario]);

  if (error) return <ErrorState error={error} />;

  const breaks = report ? Object.entries(report.breaks_by_type) : [];

  return (
    <div>
      <PageHeader title="Reconciliation" subtitle="Match rate, breaks & exception triage" />

      <ScenarioSelect scenarios={scenarios} value={scenario} onChange={setScenario} />

      {report && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total Items" value={report.total_items} hint={`${report.matched} matched`} />
            <StatCard label="Match Rate" value={pct(report.match_rate_pct)} />
            <StatCard
              label="Breaks"
              value={report.break_count}
              tone={report.break_count ? "danger" : "default"}
            />
            <StatCard label="Break Amount" value={usd(report.break_amount)} tone={report.break_amount ? "warning" : "default"} />
          </div>

          <Card className="mt-6 p-5">
            <div className="mb-3 text-sm font-semibold">Breaks by Type</div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Count</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {breaks.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={2} className="text-muted-foreground">
                      No breaks.
                    </TableCell>
                  </TableRow>
                ) : (
                  breaks.map(([type, count]) => (
                    <TableRow key={type}>
                      <TableCell>{type}</TableCell>
                      <TableCell className="text-right tabular-nums">{count}</TableCell>
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
          title="Reconciliation Copilot"
          subtitle="Ask about breaks, root causes & clearing strategy"
          avatar="⚖️"
          suggestions={[
            "What's causing the largest breaks?",
            "Which exceptions should I clear first?",
            "Summarize breaks by type.",
          ]}
        />
      </div>
    </div>
  );
}
