"use client";

import { useTranslations } from "next-intl";
import {
  Building2,
  FileText,
  Search,
  AlertTriangle,
  FileOutput,
  MessageSquare,
  Activity,
  CheckCircle,
} from "lucide-react";
import { usePlatformOverview } from "@/lib/hooks/use-super-admin";
import { OrgTable } from "./org-table";
import { cn } from "@/lib/utils";

interface OverviewCardsProps {
  onOrgClick?: (orgId: string) => void;
}

export function OverviewCards({ onOrgClick }: OverviewCardsProps) {
  const t = useTranslations("superAdmin.overview");
  const { data, isLoading } = usePlatformOverview();

  if (isLoading || !data) {
    return <div className="text-vault-text-muted text-sm">{t("loading")}</div>;
  }

  const cards = [
    {
      label: t("activeOrgs"),
      value: `${data.active_orgs_7d} / ${data.total_organizations}`,
      icon: Building2,
    },
    { label: t("workspaces"), value: data.total_workspaces, icon: FileText },
    { label: t("sources"), value: data.total_sources, icon: Search },
    { label: t("insights"), value: data.total_insights, icon: AlertTriangle },
    { label: t("deliverables"), value: data.total_deliverables, icon: FileOutput },
    { label: t("chatMessages"), value: data.total_chat_messages, icon: MessageSquare },
    {
      label: t("failedJobs24h"),
      value: data.failed_jobs_24h,
      icon: Activity,
      alert: data.failed_jobs_24h > 0,
    },
    {
      label: t("successRate7d"),
      value: `${data.job_success_rate_7d}%`,
      icon: CheckCircle,
      color:
        data.job_success_rate_7d >= 95
          ? "text-green-500"
          : data.job_success_rate_7d >= 80
            ? "text-orange-500"
            : "text-red-500",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map(({ label, value, icon: Icon, alert, color }) => (
          <div
            key={label}
            className={cn(
              "rounded-lg border border-vault-border bg-vault-surface p-4",
              alert && "border-red-500/50",
            )}
          >
            <div className="flex items-center gap-2 text-vault-text-muted">
              <Icon className={cn("h-4 w-4", color)} />
              <span className="font-mono text-[11px] uppercase tracking-wider">{label}</span>
            </div>
            <p
              className={cn(
                "mt-2 font-mono text-xl font-semibold",
                alert ? "text-red-500" : color || "text-vault-text",
              )}
            >
              {value}
            </p>
          </div>
        ))}
      </div>

      <OrgTable onOrgClick={onOrgClick} />
    </div>
  );
}
