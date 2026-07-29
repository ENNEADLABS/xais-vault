"use client";

import { useTranslations } from "next-intl";
import { AlertTriangle } from "lucide-react";
import { useErrorLog, usePlatformOverview } from "@/lib/hooks/use-super-admin";
import { cn } from "@/lib/utils";

export function HealthPanel() {
  const t = useTranslations("superAdmin.health");
  const { data: errors, isLoading: errorsLoading } = useErrorLog();
  const { data: overview } = usePlatformOverview();

  return (
    <div className="space-y-6">
      {/* Indicateurs */}
      {overview && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {/* Taux de succès */}
          <div className="rounded-lg border border-vault-border bg-vault-surface p-4">
            <p className="font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
              {t("successRate")}
            </p>
            <div className="mt-3 flex items-center gap-3">
              <div className="h-2 flex-1 rounded-full bg-vault-border">
                <div
                  className={cn(
                    "h-2 rounded-full transition-all",
                    overview.job_success_rate_7d >= 95
                      ? "bg-green-500"
                      : overview.job_success_rate_7d >= 80
                        ? "bg-orange-500"
                        : "bg-red-500",
                  )}
                  style={{ width: `${Math.min(overview.job_success_rate_7d, 100)}%` }}
                />
              </div>
              <span className="font-mono text-sm font-semibold text-vault-text">
                {overview.job_success_rate_7d}%
              </span>
            </div>
          </div>

          {/* Jobs failed 24h */}
          <div className={cn(
            "rounded-lg border bg-vault-surface p-4",
            overview.failed_jobs_24h > 0 ? "border-red-500/50" : "border-vault-border",
          )}>
            <p className="font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
              {t("failedJobs24h")}
            </p>
            <p className={cn(
              "mt-2 font-mono text-2xl font-semibold",
              overview.failed_jobs_24h > 0 ? "text-red-500" : "text-green-500",
            )}>
              {overview.failed_jobs_24h}
            </p>
          </div>
        </div>
      )}

      {/* Table des erreurs */}
      <div>
        <h3 className="mb-3 font-mono text-xs uppercase tracking-wider text-vault-text-muted">
          {t("errorLog")}
        </h3>

        {errorsLoading ? (
          <p className="text-sm text-vault-text-muted">{t("loading")}</p>
        ) : !errors || errors.length === 0 ? (
          <p className="py-8 text-center text-sm text-vault-text-muted">{t("noErrors")}</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-vault-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-vault-border bg-vault-surface">
                  <th className="px-3 py-2 text-left font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
                    {t("type")}
                  </th>
                  <th className="px-3 py-2 text-left font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
                    {t("org")}
                  </th>
                  <th className="px-3 py-2 text-left font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
                    {t("workspace")}
                  </th>
                  <th className="px-3 py-2 text-left font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
                    {t("error")}
                  </th>
                  <th className="px-3 py-2 text-left font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
                    {t("attempts")}
                  </th>
                  <th className="px-3 py-2 text-left font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
                    {t("date")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {errors.map((err) => (
                  <tr key={err.id} className="border-b border-vault-border/50 hover:bg-vault-surface/50">
                    <td className="px-3 py-2 font-mono text-xs text-vault-text">{err.type}</td>
                    <td className="px-3 py-2 text-vault-text-secondary">{err.org_name}</td>
                    <td className="px-3 py-2 text-vault-text-muted">{err.workspace_name || "—"}</td>
                    <td className="max-w-xs truncate px-3 py-2 text-xs text-red-400" title={err.error_message || ""}>
                      {err.error_message || "—"}
                    </td>
                    <td className="px-3 py-2">
                      <span className={cn(
                        "rounded px-1.5 py-0.5 font-mono text-[10px]",
                        err.attempts >= 3 ? "bg-red-500/10 text-red-400" : "text-vault-text-muted",
                      )}>
                        {err.attempts}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-vault-text-muted">
                      {new Date(err.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
