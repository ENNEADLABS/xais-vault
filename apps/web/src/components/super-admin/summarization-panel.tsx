"use client";

import { useTranslations } from "next-intl";
import { AlertTriangle, Brain, DollarSign, Zap } from "lucide-react";
import { useSummarizationStats } from "@/lib/hooks/use-super-admin";
import { cn } from "@/lib/utils";

const COST_ALERT_THRESHOLD_24H = 1.0;

export function SummarizationPanel() {
  const t = useTranslations("superAdmin.summarization");
  const { data, isLoading } = useSummarizationStats();

  if (isLoading || !data) {
    return <div className="text-vault-text-muted text-sm">{t("loading")}</div>;
  }

  if (data.total_count === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-vault-text-muted font-mono text-sm">
        {t("noData")}
      </div>
    );
  }

  const costAlert = data.cost_24h_usd > COST_ALERT_THRESHOLD_24H;

  const cards = [
    {
      label: t("totalCount"),
      value: data.total_count.toLocaleString(),
      badge: `${data.count_24h} ${t("count24h")}`,
      icon: Brain,
    },
    {
      label: t("totalCost"),
      value: `$${data.total_cost_usd.toFixed(4)}`,
      badge: `$${data.cost_24h_usd.toFixed(4)} ${t("count24h")}`,
      icon: DollarSign,
      alert: costAlert,
    },
    {
      label: t("avgCost"),
      value: `$${data.avg_cost_usd.toFixed(6)}`,
      badge: `${data.avg_input_tokens}/${data.avg_output_tokens} tok`,
      icon: Zap,
    },
  ];

  return (
    <div className="space-y-4">
      {costAlert && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/50 bg-red-500/10 px-4 py-3">
          <AlertTriangle className="h-4 w-4 text-red-500" />
          <span className="font-mono text-xs text-red-400">
            {t("alertThreshold")} ({`$${data.cost_24h_usd.toFixed(4)} > $${COST_ALERT_THRESHOLD_24H.toFixed(2)}`})
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {cards.map(({ label, value, badge, icon: Icon, alert }) => (
          <div
            key={label}
            className={cn(
              "rounded-lg border border-vault-border bg-vault-surface p-4",
              alert && "border-red-500/50",
            )}
          >
            <div className="flex items-center gap-2 text-vault-text-muted">
              <Icon className={cn("h-4 w-4", alert && "text-red-500")} />
              <span className="font-mono text-[11px] uppercase tracking-wider">
                {label}
              </span>
            </div>
            <p
              className={cn(
                "mt-2 font-mono text-xl font-semibold",
                alert ? "text-red-500" : "text-vault-text",
              )}
            >
              {value}
            </p>
            <span className="mt-1 inline-block rounded bg-vault-bg px-2 py-0.5 font-mono text-[10px] text-vault-text-muted">
              {badge}
            </span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-vault-border bg-vault-surface p-4">
          <span className="font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
            {t("avgInputTokens")}
          </span>
          <p className="mt-1 font-mono text-lg font-semibold text-vault-text">
            {data.avg_input_tokens.toLocaleString()}
          </p>
        </div>
        <div className="rounded-lg border border-vault-border bg-vault-surface p-4">
          <span className="font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
            {t("avgOutputTokens")}
          </span>
          <p className="mt-1 font-mono text-lg font-semibold text-vault-text">
            {data.avg_output_tokens.toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  );
}
