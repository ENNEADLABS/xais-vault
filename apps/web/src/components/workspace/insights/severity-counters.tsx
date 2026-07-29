"use client";

import { cn } from "@/lib/utils";
import type { Insight } from "@/types/api";

// ─── Compteurs de sévérité ───────────────────────────────

interface SeverityCountersProps {
  insights: Insight[];
}

const SEVERITY_ORDER: Insight["severity"][] = ["critical", "high", "medium", "low"];

const SEVERITY_CONFIG: Record<Insight["severity"], { dot: string; label: string }> = {
  critical: { dot: "bg-vault-danger", label: "Critical" },
  high: { dot: "bg-vault-warning", label: "High" },
  medium: { dot: "bg-vault-medium", label: "Medium" },
  low: { dot: "bg-vault-low", label: "Low" },
};

export function SeverityCounters({ insights }: SeverityCountersProps) {
  const counts = insights.reduce(
    (acc, f) => {
      acc[f.severity] = (acc[f.severity] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {SEVERITY_ORDER.map((sev) => {
        const count = counts[sev] ?? 0;
        if (count === 0) return null;
        const config = SEVERITY_CONFIG[sev];
        return (
          <div key={sev} className="flex items-center gap-1.5">
            <span className={cn("h-2 w-2 rounded-full", config.dot)} />
            <span className="text-[12px] font-mono text-vault-text-muted">
              {count} {config.label}
            </span>
          </div>
        );
      })}
      <span className="text-[12px] text-vault-text-secondary ml-auto">
        {insights.length} total
      </span>
    </div>
  );
}
