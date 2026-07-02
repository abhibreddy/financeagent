"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Bell, Bot, FileText, TrendingUp, LineChart, Sparkles, Home, Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";

type Item = { href: string; label: string; icon: React.ComponentType<{ className?: string }> };

const HOME: Item = { href: "/", label: "Home", icon: Home };

const FINANCE: Item[] = [
  { href: "/finance/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/finance/alerts", label: "Alert Queue", icon: Bell },
  { href: "/finance/chat", label: "Agent Chat", icon: Bot },
  { href: "/finance/invoices", label: "Invoice Fraud", icon: FileText },
];

const TRADING: Item[] = [
  { href: "/trading/dashboard", label: "Trading Dashboard", icon: LineChart },
  { href: "/trading/agent", label: "Portfolio Agent", icon: Bot },
  { href: "/trading/forecaster", label: "Stock Forecaster", icon: Sparkles },
];

function NavLink({ item, active }: { item: Item; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-sidebar-primary text-sidebar-primary-foreground"
          : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
      )}
    >
      <Icon className="size-4 shrink-0" />
      {item.label}
    </Link>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-3 pt-4 pb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
      {children}
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex items-center gap-2 px-4 py-5">
        <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Shield className="size-4" />
        </div>
        <div>
          <div className="text-sm font-semibold leading-tight">RT ERP</div>
          <div className="text-xs text-muted-foreground leading-tight">Finance &amp; Trading</div>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
        <NavLink item={HOME} active={isActive(HOME.href)} />
        <SectionLabel>Finance</SectionLabel>
        {FINANCE.map((i) => (
          <NavLink key={i.href} item={i} active={isActive(i.href)} />
        ))}
        <SectionLabel>Trading</SectionLabel>
        {TRADING.map((i) => (
          <NavLink key={i.href} item={i} active={isActive(i.href)} />
        ))}
      </nav>

      <div className="flex items-center gap-2 border-t border-sidebar-border px-4 py-3 text-xs text-muted-foreground">
        <TrendingUp className="size-3.5" />
        Azure OpenAI · Langfuse
      </div>
    </aside>
  );
}
