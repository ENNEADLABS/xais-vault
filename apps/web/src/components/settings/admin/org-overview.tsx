"use client";

import { useTranslations } from "next-intl";
import { useAdminOverview } from "@/lib/hooks/use-admin";

interface StatCardProps {
  label: string;
  value: number | string;
}

function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="rounded-lg border border-vault-border bg-vault-surface px-4 py-3">
      <p className="font-mono text-[11px] uppercase tracking-widest text-vault-text-muted mb-1">
        {label}
      </p>
      <p className="text-2xl font-semibold text-vault-text tabular-nums">{value}</p>
    </div>
  );
}

export function OrgOverview() {
  const t = useTranslations("settings.admin");
  const { data, isLoading, isError } = useAdminOverview();
  const overview = data?.data;

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-18 rounded-lg border border-vault-border bg-vault-surface animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (isError || !overview) {
    return (
      <p className="text-sm text-vault-text-muted">{t("overviewError")}</p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard label={t("members")} value={overview.member_count} />
      <StatCard label={t("workspaces")} value={overview.workspace_count} />
      <StatCard label={t("sources")} value={overview.source_count} />
      <StatCard label={t("insights")} value={overview.insight_count} />
    </div>
  );
}
