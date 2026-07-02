"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { InvoiceReport, InvoiceRecord } from "@/lib/types";
import { usd } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { LoadingState, ErrorState } from "../dashboard/page";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const CATEGORIES: { key: keyof InvoiceReport; label: string }[] = [
  { key: "exact_duplicates", label: "Exact Duplicates" },
  { key: "near_duplicates", label: "Near Duplicates" },
  { key: "split_billing", label: "Split Billing" },
  { key: "threshold_avoidance", label: "Threshold Avoidance" },
  { key: "ghost_vendors", label: "Ghost Vendors" },
];

function InvoiceTable({ rows }: { rows: InvoiceRecord[] }) {
  if (!rows.length) return <p className="py-6 text-sm text-muted-foreground">None detected.</p>;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Invoice</TableHead>
          <TableHead>Vendor</TableHead>
          <TableHead>Amount</TableHead>
          <TableHead>Date</TableHead>
          <TableHead>Department</TableHead>
          <TableHead>Approver</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={r.invoice_id}>
            <TableCell className="font-medium">{r.invoice_id}</TableCell>
            <TableCell>{r.vendor}</TableCell>
            <TableCell className="tabular-nums">{usd(r.amount)}</TableCell>
            <TableCell>{String(r.date).slice(0, 10)}</TableCell>
            <TableCell>{r.department}</TableCell>
            <TableCell>{r.approver}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export default function InvoiceFraud() {
  const [report, setReport] = useState<InvoiceReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.invoicesReport().then(setReport).catch((e) => setError(String(e)));
  }, []);

  if (error) return <ErrorState error={error} />;
  if (!report) return <LoadingState />;

  return (
    <div>
      <PageHeader title="Invoice Fraud" subtitle="Duplicate, split, threshold-avoidance & ghost-vendor detection" />
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Total Invoices" value={report.total_invoices} />
        <StatCard label="Flagged" value={report.flagged_count} tone={report.flagged_count ? "warning" : "default"} />
        <StatCard label="Flagged Amount" value={usd(report.total_flagged_amount)} />
      </div>

      <Card className="mt-6 p-5">
        <Tabs defaultValue={CATEGORIES[0].key as string}>
          <TabsList className="flex-wrap">
            {CATEGORIES.map((c) => {
              const n = (report[c.key] as InvoiceRecord[]).length;
              return (
                <TabsTrigger key={c.key as string} value={c.key as string}>
                  {c.label} ({n})
                </TabsTrigger>
              );
            })}
          </TabsList>
          {CATEGORIES.map((c) => (
            <TabsContent key={c.key as string} value={c.key as string}>
              <InvoiceTable rows={report[c.key] as InvoiceRecord[]} />
            </TabsContent>
          ))}
        </Tabs>
      </Card>
    </div>
  );
}
