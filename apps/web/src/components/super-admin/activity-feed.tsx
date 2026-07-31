"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import {
  FileSearch,
  FileText,
  FileOutput,
  Webhook,
  Search,
  Zap,
} from "lucide-react";
import { useGlobalActivity } from "@/lib/hooks/use-super-admin";
import { UserActivityTable } from "./user-activity-table";
import { cn } from "@/lib/utils";

const TYPE_ICONS: Record<string, React.ElementType> = {
  index_source: FileText,
  scan_workspace: FileSearch,
  verify_insight: Search,
  investigate: Zap,
  generate_deliverable: FileOutput,
  dispatch_webhook: Webhook,
};

const STATUS_CLASSES: Record<string, string> = {
  completed: "bg-green-500/10 text-green-400",
  processing: "bg-orange-500/10 text-orange-400",
  pending: "bg-vault-border text-vault-text-muted",
  failed: "bg-red-500/10 text-red-400",
};

interface ActivityFeedProps {
  initialOrgId?: string;
}

export function ActivityFeed({ initialOrgId = "" }: ActivityFeedProps) {
  const t = useTranslations("superAdmin.activity");
  const { data: items, isLoading } = useGlobalActivity();
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [orgFilter, setOrgFilter] = useState<string>("");

  // Extraire les types et orgs uniques pour les filtres
  const { types, orgNames } = useMemo(() => {
    if (!items) return { types: [], orgNames: [] };
    return {
      types: [...new Set(items.map((i) => i.type))].sort(),
      orgNames: [...new Set(items.map((i) => i.org_name))].sort(),
    };
  }, [items]);

  const filtered = useMemo(() => {
    if (!items) return [];
    return items.filter((item) => {
      if (typeFilter && item.type !== typeFilter) return false;
      if (orgFilter && item.org_name !== orgFilter) return false;
      return true;
    });
  }, [items, typeFilter, orgFilter]);

  if (isLoading) {
    return <div className="text-vault-text-muted text-sm">{t("loading")}</div>;
  }

  return (
    <div className="space-y-6">
      {/* Filtres */}
      <div className="flex gap-3">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded border border-vault-border bg-vault-surface px-2 py-1 font-mono text-xs text-vault-text"
        >
          <option value="">{t("allTypes")}</option>
          {types.map((type) => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>
        <select
          value={orgFilter}
          onChange={(e) => setOrgFilter(e.target.value)}
          className="rounded border border-vault-border bg-vault-surface px-2 py-1 font-mono text-xs text-vault-text"
        >
          <option value="">{t("allOrgs")}</option>
          {orgNames.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
      </div>

      {/* Feed */}
      <div className="space-y-1">
        {filtered.map((item) => {
          const Icon = TYPE_ICONS[item.type] || Zap;
          return (
            <div
              key={item.id}
              className="flex items-center gap-3 rounded-md border border-vault-border/50 bg-vault-surface px-3 py-2"
            >
              <Icon className="h-4 w-4 shrink-0 text-vault-text-muted" />
              <span className="font-mono text-xs text-vault-accent">{item.org_name}</span>
              <span className="text-xs text-vault-text-secondary">{item.type}</span>
              {item.workspace_name && (
                <span className="text-xs text-vault-text-muted">— {item.workspace_name}</span>
              )}
              <div className="ml-auto flex items-center gap-2">
                <span className={cn(
                  "rounded px-1.5 py-0.5 font-mono text-[10px] uppercase",
                  STATUS_CLASSES[item.status] || STATUS_CLASSES.pending,
                )}>
                  {item.status}
                </span>
                <span className="font-mono text-[10px] text-vault-text-muted">
                  {new Date(item.created_at).toLocaleTimeString()}
                </span>
              </div>
            </div>
          );
        })}
        {filtered.length === 0 && (
          <p className="py-8 text-center text-sm text-vault-text-muted">{t("empty")}</p>
        )}
      </div>

      {/* Tableau utilisateurs */}
      <UserActivityTable initialOrgId={initialOrgId} />
    </div>
  );
}
