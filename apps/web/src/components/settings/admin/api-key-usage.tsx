"use client";

import { useTranslations } from "next-intl";
import { useAdminApiKeysUsage } from "@/lib/hooks/use-admin";
import { cn } from "@/lib/utils";

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  });
}

export function ApiKeyUsage() {
  const t = useTranslations("settings.admin");
  const { data, isLoading } = useAdminApiKeysUsage();
  const keys = data?.data?.keys ?? [];

  if (isLoading) {
    return (
      <div className="space-y-1">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-8 rounded bg-vault-surface animate-pulse" />
        ))}
      </div>
    );
  }

  if (keys.length === 0) {
    return <p className="text-sm text-vault-text-muted">{t("noApiKeys")}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="border-b border-vault-border">
            <th className="text-left py-2 pr-4 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">{t("keyName")}</th>
            <th className="text-left py-2 pr-4 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">{t("prefix")}</th>
            <th className="text-right py-2 px-3 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">RPM</th>
            <th className="text-right py-2 px-3 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">RPD</th>
            <th className="text-right py-2 px-3 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">{t("lastUsed")}</th>
            <th className="text-right py-2 pl-3 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">{t("keyStatus")}</th>
          </tr>
        </thead>
        <tbody>
          {keys.map((key) => (
            <tr key={key.id} className="border-b border-vault-border/50">
              <td className="py-1.5 pr-4 text-vault-text max-w-32 truncate">{key.name}</td>
              <td className="py-1.5 pr-4 font-mono text-vault-text-muted">{key.key_prefix}…</td>
              <td className="py-1.5 px-3 text-right tabular-nums text-vault-text-muted">{key.rpm_limit}</td>
              <td className="py-1.5 px-3 text-right tabular-nums text-vault-text-muted">{key.rpd_limit}</td>
              <td className="py-1.5 px-3 text-right tabular-nums text-vault-text-muted font-mono text-[11px]">
                {fmtDate(key.last_used_at)}
              </td>
              <td className="py-1.5 pl-3 text-right">
                <span
                  className={cn(
                    "inline-block px-2 py-0.5 rounded text-[10px] font-medium",
                    key.is_active
                      ? "text-green-400 bg-green-400/10"
                      : "text-vault-text-muted bg-vault-surface",
                  )}
                >
                  {key.is_active ? t("active") : t("inactive")}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
