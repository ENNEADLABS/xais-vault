"use client";

import { useTranslations } from "next-intl";
import { cn, formatRelativeDate } from "@/lib/utils";
import type { Source } from "@/types/api";

interface StatusBarProps {
  sources: Source[];
  scanStatus: string;
  lastUpdated?: string;
  className?: string;
}

/** Barre de statut compacte affichée en bas de la page workspace */
export function StatusBar({ sources, scanStatus, lastUpdated, className }: StatusBarProps) {
  const t = useTranslations("workspace_page");

  const readyCount = sources.filter((s) => s.status === "ready").length;
  const processingCount = sources.filter((s) => s.status === "processing").length;

  const scanColorClass =
    scanStatus === "scanned" || scanStatus === "completed"
      ? "text-vault-success"
      : scanStatus === "scanning"
        ? "text-vault-accent animate-[vault-pulse_1.5s_ease-in-out_infinite]"
        : scanStatus === "failed"
          ? "text-vault-danger"
          : "text-vault-text-muted";

  return (
    <div
      className={cn(
        "flex h-6 items-center justify-between border-t border-vault-border bg-vault-status-bar px-3.5 font-mono text-[11px] text-vault-text-muted",
        className,
      )}
    >
      <span>
        {t("statusBarSources")}{" "}
        <span className="text-vault-success">{t("statusBarReady", { count: readyCount })}</span>
        {" · "}
        <span className={cn("text-vault-accent", processingCount > 0 && "animate-[vault-pulse_1.5s_ease-in-out_infinite]")}>
          {t("statusBarProcessing", { count: processingCount })}
        </span>
      </span>
      <span>
        {t("statusBarScan")} <span className={scanColorClass}>{scanStatus}</span>
      </span>
      <span className="font-mono">
        {lastUpdated ? formatRelativeDate(lastUpdated, "fr") : "—"}
      </span>
    </div>
  );
}
