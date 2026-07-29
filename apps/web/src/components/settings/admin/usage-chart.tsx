"use client";

import { useTranslations } from "next-intl";
import { useAdminUsage } from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";

const OPERATION_COLORS: Record<string, string> = {
  chat: "bg-blue-500",
  scan: "bg-vault-accent",
  verify: "bg-green-500",
  investigate: "bg-orange-500",
  deliverable: "bg-purple-500",
};

const OPERATION_LABELS: Record<string, string> = {
  chat: "Chat",
  scan: "Scan",
  verify: "Vérif.",
  investigate: "Recherche",
  deliverable: "Livrable",
};

export function UsageChart() {
  const t = useTranslations("settings.admin");
  const { data, isLoading } = useAdminUsage(6);
  const stats = data?.data;

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-7 rounded bg-vault-surface animate-pulse" />
        ))}
      </div>
    );
  }

  if (!stats || stats.months.length === 0) {
    return <p className="text-sm text-vault-text-muted">{t("noUsageData")}</p>;
  }

  // Grouper par mois
  const monthMap = new Map<string, Record<string, number>>();
  for (const row of stats.months) {
    if (!monthMap.has(row.month)) monthMap.set(row.month, {});
    monthMap.get(row.month)![row.operation] = row.count;
  }

  const months = Array.from(monthMap.entries()).slice(0, 6).reverse();
  const maxTotal = Math.max(
    ...months.map(([, ops]) => Object.values(ops).reduce((a, b) => a + b, 0)),
    1,
  );

  return (
    <div className="space-y-2">
      {/* Légende */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3">
        {Object.entries(OPERATION_LABELS).map(([op, label]) => (
          <div key={op} className="flex items-center gap-1.5">
            <span className={cn("inline-block w-2.5 h-2.5 rounded-sm", OPERATION_COLORS[op] ?? "bg-vault-text-muted")} />
            <span className="text-[11px] text-vault-text-muted">{label}</span>
          </div>
        ))}
      </div>

      {/* Barres par mois */}
      {months.map(([month, ops]) => {
        const total = Object.values(ops).reduce((a, b) => a + b, 0);
        const widthPct = (total / maxTotal) * 100;

        return (
          <div key={month} className="flex items-center gap-3">
            <span className="font-mono text-[11px] text-vault-text-muted w-14 shrink-0 text-right">
              {month}
            </span>
            <div className="flex-1 h-5 bg-vault-surface rounded overflow-hidden flex">
              {Object.entries(ops).map(([op, count]) => {
                const opPct = (count / maxTotal) * 100;
                return (
                  <div
                    key={op}
                    title={`${OPERATION_LABELS[op] ?? op}: ${count}`}
                    style={{ width: `${opPct}%` }}
                    className={cn(
                      "h-full transition-all",
                      OPERATION_COLORS[op] ?? "bg-vault-text-muted",
                    )}
                  />
                );
              })}
            </div>
            <span className="font-mono text-[11px] text-vault-text-muted w-8 text-right tabular-nums">
              {total}
            </span>
          </div>
        );
      })}
    </div>
  );
}
