"use client";

import { useTranslations } from "next-intl";
import { useAdminActivity } from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  completed: "text-green-400 bg-green-400/10",
  failed: "text-red-400 bg-red-400/10",
  processing: "text-yellow-400 bg-yellow-400/10",
  pending: "text-vault-text-muted bg-vault-surface",
};

const JOB_TYPE_LABELS: Record<string, string> = {
  index_source: "Indexation",
  scan_workspace: "Scan",
  verify_insight: "Vérif.",
  investigate: "Recherche",
  generate_deliverable: "Livrable",
  dispatch_webhook: "Webhook",
};

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ActivityLog() {
  const t = useTranslations("settings.admin");
  const { data, isLoading } = useAdminActivity(50);
  const items = data?.data?.items ?? [];

  if (isLoading) {
    return (
      <div className="space-y-1">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-8 rounded bg-vault-surface animate-pulse" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return <p className="text-sm text-vault-text-muted">{t("noActivity")}</p>;
  }

  return (
    <div className="overflow-x-auto max-h-72 overflow-y-auto">
      <table className="w-full text-[12px]">
        <thead className="sticky top-0 bg-vault-bg">
          <tr className="border-b border-vault-border">
            <th className="text-left py-2 pr-4 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
              {t("jobType")}
            </th>
            <th className="text-left py-2 pr-4 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
              {t("workspace")}
            </th>
            <th className="text-left py-2 pr-4 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
              {t("status")}
            </th>
            <th className="text-right py-2 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
              {t("date")}
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-b border-vault-border/40 hover:bg-vault-surface/50">
              <td className="py-1.5 pr-4 text-vault-text-secondary">
                {JOB_TYPE_LABELS[item.type] ?? item.type}
              </td>
              <td className="py-1.5 pr-4 text-vault-text-muted max-w-32 truncate">
                {item.workspace_name ?? item.source_name ?? "—"}
              </td>
              <td className="py-1.5 pr-4">
                <span
                  className={cn(
                    "inline-block px-2 py-0.5 rounded text-[10px] font-medium",
                    STATUS_STYLES[item.status] ?? STATUS_STYLES.pending,
                  )}
                >
                  {item.status}
                </span>
              </td>
              <td className="py-1.5 text-right tabular-nums text-vault-text-muted font-mono text-[11px]">
                {fmtDate(item.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
