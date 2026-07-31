"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { ArrowUpDown } from "lucide-react";
import { useUserActivity, useOrgMetrics } from "@/lib/hooks/use-super-admin";
import { cn } from "@/lib/utils";

type SortKey = "email" | "org_name" | "workspaces_created" | "sources_uploaded" | "chat_messages_sent" | "last_active_at";

interface UserActivityTableProps {
  initialOrgId?: string;
}

export function UserActivityTable({ initialOrgId = "" }: UserActivityTableProps) {
  return (
    <UserActivityTableContent
      key={initialOrgId}
      initialOrgId={initialOrgId}
    />
  );
}

function UserActivityTableContent({ initialOrgId }: Required<UserActivityTableProps>) {
  const t = useTranslations("superAdmin.userTable");
  const [orgFilter, setOrgFilter] = useState<string>(initialOrgId);
  const [sortKey, setSortKey] = useState<SortKey>("last_active_at");
  const [sortAsc, setSortAsc] = useState(false);
  const [now] = useState(() => Date.now());

  const { data: users, isLoading } = useUserActivity(orgFilter || undefined);
  const { data: orgs } = useOrgMetrics();

  const sorted = useMemo(() => {
    if (!users) return [];
    return [...users].sort((a, b) => {
      const va = a[sortKey] ?? "";
      const vb = b[sortKey] ?? "";
      const cmp = typeof va === "number" ? va - (vb as number) : String(va).localeCompare(String(vb));
      return sortAsc ? cmp : -cmp;
    });
  }, [users, sortKey, sortAsc]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  }

  const columns: { key: SortKey; label: string }[] = [
    { key: "email", label: t("email") },
    { key: "org_name", label: t("org") },
    { key: "workspaces_created", label: t("workspaces") },
    { key: "sources_uploaded", label: t("sources") },
    { key: "chat_messages_sent", label: t("messages") },
    { key: "last_active_at", label: t("lastActive") },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-xs uppercase tracking-wider text-vault-text-muted">
          {t("title")}
        </h3>
        <select
          value={orgFilter}
          onChange={(e) => setOrgFilter(e.target.value)}
          className="rounded border border-vault-border bg-vault-surface px-2 py-1 font-mono text-xs text-vault-text"
        >
          <option value="">{t("allOrgs")}</option>
          {orgs?.map((org) => (
            <option key={org.org_id} value={org.org_id}>{org.org_name}</option>
          ))}
        </select>
      </div>

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
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-vault-text-muted">
                  {t("loading")}
                </td>
              </tr>
            ) : sorted.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-vault-text-muted">
                  {t("empty")}
                </td>
              </tr>
            ) : (
              sorted.map((user) => (
                <tr key={user.user_id} className="border-b border-vault-border/50 hover:bg-vault-surface/50">
                  <td className="px-3 py-2">
                    <div>
                      <p className="text-vault-text">{user.display_name || "—"}</p>
                      <p className="text-[11px] text-vault-text-muted">{user.email}</p>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-vault-text-secondary">{user.org_name}</td>
                  <td className="px-3 py-2 text-vault-text-secondary">{user.workspaces_created}</td>
                  <td className="px-3 py-2 text-vault-text-secondary">{user.sources_uploaded}</td>
                  <td className="px-3 py-2 text-vault-text-secondary">{user.chat_messages_sent}</td>
                  <td className={cn("px-3 py-2 font-mono text-xs", getActivityClass(user.last_active_at, now))}>
                    {user.last_active_at
                      ? new Date(user.last_active_at).toLocaleDateString()
                      : "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function getActivityClass(lastActive: string | null, now: number): string {
  if (!lastActive) return "text-vault-text-muted";
  const hours = (now - new Date(lastActive).getTime()) / 3_600_000;
  if (hours < 24) return "text-green-400";
  if (hours < 168) return "text-vault-text-secondary";
  return "text-vault-text-muted";
}
