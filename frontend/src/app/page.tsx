import Link from "next/link";
import { Shield, TrendingUp, LayoutDashboard, Bell, Bot, FileText, LineChart, Sparkles } from "lucide-react";

const MODULES = [
  {
    href: "/finance/dashboard",
    icon: Shield,
    title: "Finance Agent",
    desc: "Real-time fraud detection: alert triage, conversational investigation, and invoice fraud scanning.",
    functions: [
      { icon: LayoutDashboard, label: "Dashboard" },
      { icon: Bell, label: "Alert Queue" },
      { icon: Bot, label: "Agent Chat" },
      { icon: FileText, label: "Invoice Fraud" },
    ],
  },
  {
    href: "/trading/dashboard",
    icon: TrendingUp,
    title: "Trading Agent",
    desc: "Portfolio analytics, a multi-agent portfolio analyst, and FinGPT-style single-stock forecasting.",
    functions: [
      { icon: LineChart, label: "Trading Dashboard" },
      { icon: Bot, label: "Portfolio Agent" },
      { icon: Sparkles, label: "Stock Forecaster" },
    ],
  },
];

export default function Home() {
  return (
    <div>
      <header className="mb-8">
        <h1 className="text-2xl font-semibold">RT ERP</h1>
        <p className="text-muted-foreground">Choose a module to get started</p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        {MODULES.map((m) => {
          const Icon = m.icon;
          return (
            <Link
              key={m.href}
              href={m.href}
              className="group flex min-h-[420px] flex-col rounded-xl border border-border bg-card p-7 shadow-sm transition-all hover:-translate-y-1 hover:border-foreground/20 hover:shadow-lg"
            >
              <div className="mb-3 flex size-12 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Icon className="size-6" />
              </div>
              <h2 className="text-xl font-semibold">{m.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{m.desc}</p>
              <div className="mt-6 mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Functions
              </div>
              <ul className="space-y-2">
                {m.functions.map((f) => {
                  const F = f.icon;
                  return (
                    <li key={f.label} className="flex items-center gap-3 text-sm text-foreground/80">
                      <F className="size-4 text-muted-foreground" />
                      {f.label}
                    </li>
                  );
                })}
              </ul>
              <span className="mt-auto pt-6 text-sm font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
                Open {m.title} →
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
