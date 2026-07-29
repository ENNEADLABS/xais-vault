"use client";

import { useTranslations } from "next-intl";
import { useAdminUsage } from "@/lib/hooks/use-admin";

function fmt(n: number): string {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(n);
}

function fmtCost(n: number): string {
  return `$${n.toFixed(4)}`;
}

export function CostBreakdown() {
  const t = useTranslations("settings.admin");
  const { data, isLoading } = useAdminUsage(6);
  const stats = data?.data;

  if (isLoading) {
    return (
      <div className="space-y-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-7 rounded bg-vault-surface animate-pulse" />
        ))}
      </div>
    );
  }

  if (!stats || stats.months.length === 0) {
    return <p className="text-sm text-vault-text-muted">{t("noUsageData")}</p>;
  }

  // Agréger par opération (toutes périodes confondues)
  const byOp = new Map<string, { count: number; tokens_in: number; tokens_out: number; cost: number }>();
  for (const row of stats.months) {
    const existing = byOp.get(row.operation) ?? { count: 0, tokens_in: 0, tokens_out: 0, cost: 0 };
    byOp.set(row.operation, {
      count: existing.count + row.count,
      tokens_in: existing.tokens_in + row.input_tokens,
      tokens_out: existing.tokens_out + row.output_tokens,
      cost: existing.cost + row.cost_usd,
    });
  }

  const rows = Array.from(byOp.entries()).sort((a, b) => b[1].cost - a[1].cost);
  const totals = stats.totals;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="border-b border-vault-border">
            <th className="text-left py-2 pr-4 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
              {t("operation")}
            </th>
            <th className="text-right py-2 px-3 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
              {t("requests")}
            </th>
            <th className="text-right py-2 px-3 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
              {t("tokensIn")}
            </th>
            <th className="text-right py-2 px-3 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
              {t("tokensOut")}
            </th>
            <th className="text-right py-2 pl-3 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
              {t("cost")}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([op, d]) => (
            <tr key={op} className="border-b border-vault-border/50">
              <td className="py-1.5 pr-4 text-vault-text-secondary capitalize">{op}</td>
              <td className="py-1.5 px-3 text-right tabular-nums text-vault-text-muted">{fmt(d.count)}</td>
              <td className="py-1.5 px-3 text-right tabular-nums text-vault-text-muted">{fmt(d.tokens_in)}</td>
              <td className="py-1.5 px-3 text-right tabular-nums text-vault-text-muted">{fmt(d.tokens_out)}</td>
              <td className="py-1.5 pl-3 text-right tabular-nums text-vault-text">{fmtCost(d.cost)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td className="py-2 pr-4 font-semibold text-vault-text">{t("total")}</td>
            <td className="py-2 px-3 text-right tabular-nums font-semibold text-vault-text">{fmt(totals.total_operations)}</td>
            <td className="py-2 px-3 text-right tabular-nums font-semibold text-vault-text">{fmt(totals.total_input_tokens)}</td>
            <td className="py-2 px-3 text-right tabular-nums font-semibold text-vault-text">{fmt(totals.total_output_tokens)}</td>
            <td className="py-2 pl-3 text-right tabular-nums font-semibold text-vault-text">{fmtCost(totals.total_cost_usd)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
