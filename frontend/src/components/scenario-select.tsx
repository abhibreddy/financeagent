"use client";

import type { SuiteScenario } from "@/lib/types";

/** Native scenario picker styled to match the Input component. */
export function ScenarioSelect({
  scenarios,
  value,
  onChange,
}: {
  scenarios: SuiteScenario[];
  value: string;
  onChange: (id: string) => void;
}) {
  const active = scenarios.find((s) => s.id === value);
  return (
    <div className="max-w-md">
      <label className="mb-1 block text-sm font-medium">Scenario</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={scenarios.length === 0}
        className="flex h-9 w-full rounded-md border border-border bg-input-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
      >
        {scenarios.length === 0 && <option>Loading…</option>}
        {scenarios.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>
      {active && <p className="mt-1 text-xs text-muted-foreground">{active.description}</p>}
    </div>
  );
}
