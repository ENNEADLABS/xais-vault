"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { ArrowUpDown } from "lucide-react";
import { useOrgMetrics } from "@/lib/hooks/use-super-admin";
import { cn } from "@/lib/utils";

type SortKey = "org_name" | "member_count" | "workspace_count" | "source_count" | "insight_count" | "chat_message_count" | "deliverable_count" | "last_activity_at";

interface OrgTableProps {
  onOrgClick?: (orgId: string) => void;
}

export function OrgTable({ onOrgClick }: OrgTableProps) {
  const t = useTranslations("superAdmin.orgTable");
  const { data: orgs, isLoading } = useOrgMetrics();
  const [sortKey, setSortKey] = useState<SortKey>("last_activity_at");
  const [sortAsc, setSortAsc] = useState(false);

  const sorted = useMemo(() => {
    if (!orgs) return [];
    return [...orgs].sort((a, b) => {
      const va = a[sortKey] ?? "";
      const vb = b[sortKey] ?? "";
      const cmp = typeof va === "number" ? va - (vb as number) : String(va).localeCompare(String(vb));
      return sortAsc ? cmp : -cmp;
    });
  }, [orgs, sortKey, sortAsc]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  }

  if (isLoading) return <div className="text-vault-text-muted text-sm">{t("loading")}</div>;

  const columns: { key: SortKey; label: string }[] = [
    { key: "org_name", label: t("name") },
    { key: "member_count", label: t("members") },
    { key: "workspace_count", label: t("workspaces") },
    { key: "source_count", label: t("sources") },
    { key: "insight_count", label: t("insights") },
    { key: "chat_message_count", label: t("messages") },
    { key: "deliverable_count", label: t("deliverables") },
    { key: "last_activity_at", label: t("lastActivity") },
  ];

  return (
    <div className="overflow-x-auto rounded-lg border border-vault-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-vault-border bg-vault-surface">
            {columns.map(({ key, label }) => (
              <th key={key} className="px-3 py-2 text-left">
                <button
                  type="button"
                  onClick={() => toggleSort(key)}
                  className="flex items-center gap-1 font-mono text-[11px] uppercase tracking-wider text-vault-text-muted hover:text-vault-text"
                >
                  {label}
                  <ArrowUpDown className="h-3 w-3" />
                </button>
              </th>
            ))}
            <th className="px-3 py-2 text-left font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
              {t("plan")}
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((org) => (
            <tr
              key={org.org_id}
              onClick={() => onOrgClick?.(org.org_id)}
              className={cn(
                "border-b border-vault-border/50 hover:bg-vault-surface/50",
                onOrgClick && "cursor-pointer",
              )}
            >
              <td className="px-3 py-2 font-medium text-vault-text">{org.org_name}</td>
              <td className="px-3 py-2 text-vault-text-secondary">{org.member_count}</td>
              <td className="px-3 py-2 text-vault-text-secondary">{org.workspace_count}</td>
              <td className="px-3 py-2 text-vault-text-secondary">{org.source_count}</td>
              <td className="px-3 py-2 text-vault-text-secondary">{org.insight_count}</td>
              <td className="px-3 py-2 text-vault-text-secondary">{org.chat_message_count}</td>
              <td className="px-3 py-2 text-vault-text-secondary">{org.deliverable_count}</td>
              <td className="px-3 py-2 text-vault-text-muted font-mono text-xs">
                {org.last_activity_at
                  ? new Date(org.last_activity_at).toLocaleDateString()
                  : "—"}
              </td>
              <td className="px-3 py-2">
                <span className={cn(
                  "rounded px-1.5 py-0.5 font-mono text-[10px] uppercase",
                  org.plan === "enterprise" && "bg-purple-500/10 text-purple-400",
                  org.plan === "premium" && "bg-blue-500/10 text-blue-400",
                  org.plan === "team" && "bg-green-500/10 text-green-400",
                  org.plan === "trial" && "bg-orange-500/10 text-orange-400",
                  org.plan === "starter" && "bg-vault-border text-vault-text-muted",
                )}>
                  {org.plan}
                </span>
              </td>
            </tr>
          ))}
          {sorted.length === 0 && (
            <tr>
              <td colSpan={9} className="px-3 py-8 text-center text-vault-text-muted">
                {t("empty")}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
