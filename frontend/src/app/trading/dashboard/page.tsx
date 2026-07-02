"use client";

import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "@/lib/api";
import type { PortfolioReport, Position } from "@/lib/types";
import { usd, pct } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { LoadingState, ErrorState } from "@/app/finance/dashboard/page";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function TradingDashboard() {
  const [report, setReport] = useState<PortfolioReport | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [priceSeries, setPriceSeries] = useState<{ date: string; close: number }[]>([]);
  const [ticker, setTicker] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.portfolio()
      .then((d) => {
        setReport(d.report);
        setPositions(d.positions);
        if (d.positions[0]) setTicker(d.positions[0].ticker);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!ticker) return;
    api.prices(ticker).then((d) => setPriceSeries(d.prices.map((p) => ({ date: p.date.slice(0, 10), close: p.close })))).catch(() => {});
  }, [ticker]);

  if (error) return <ErrorState error={error} />;
  if (!report) return <LoadingState />;

  const { portfolio, exposure, risk } = report;
  const sectorData = Object.entries(exposure.sector_exposure).map(([sector, value]) => ({ sector, value }));

  return (
    <div>
      <PageHeader title="Trading Dashboard" subtitle="Portfolio analytics & risk" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Market Value" value={usd(portfolio.total_market_value)} />
        <StatCard
          label="Unrealized P&L"
          value={usd(portfolio.unrealized_pnl)}
          hint={pct(portfolio.unrealized_pnl_pct)}
          tone={portfolio.unrealized_pnl >= 0 ? "default" : "danger"}
        />
        <StatCard
          label="Concentration"
          value={exposure.concentration_level}
          hint={`${exposure.largest_position} ${pct(exposure.largest_weight_pct)}`}
          tone={exposure.concentration_level === "High" ? "danger" : "default"}
        />
        <StatCard
          label="Risk Score"
          value={`${risk.risk_score}/100`}
          hint={risk.risk_level}
          tone={risk.risk_level === "High" ? "danger" : "default"}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <div className="mb-4 text-sm font-semibold">Sector Exposure</div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={sectorData} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis type="category" dataKey="sector" tick={{ fontSize: 12 }} width={80} />
              <Tooltip formatter={(v) => `${v}%`} />
              <Bar dataKey="value" fill="var(--chart-3)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="text-sm font-semibold">Price History</div>
            <select
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            >
              {positions.map((p) => (
                <option key={p.ticker} value={p.ticker}>
                  {p.ticker}
                </option>
              ))}
            </select>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={priceSeries}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={40} />
              <YAxis tick={{ fontSize: 12 }} domain={["auto", "auto"]} />
              <Tooltip />
              <Line type="monotone" dataKey="close" stroke="var(--chart-1)" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card className="mt-6 p-5">
        <div className="mb-3 text-sm font-semibold">Positions</div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ticker</TableHead>
              <TableHead>Sector</TableHead>
              <TableHead>Qty</TableHead>
              <TableHead>Avg Cost</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Market Value</TableHead>
              <TableHead>Weight</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {positions.map((p) => (
              <TableRow key={p.ticker}>
                <TableCell className="font-medium">{p.ticker}</TableCell>
                <TableCell>{p.sector}</TableCell>
                <TableCell className="tabular-nums">{p.quantity.toLocaleString()}</TableCell>
                <TableCell className="tabular-nums">{usd(p.avg_cost)}</TableCell>
                <TableCell className="tabular-nums">{usd(p.current_price)}</TableCell>
                <TableCell className="tabular-nums">{usd(p.quantity * p.current_price)}</TableCell>
                <TableCell className="tabular-nums">{pct(portfolio.weights[p.ticker])}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
