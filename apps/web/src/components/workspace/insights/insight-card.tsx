"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FileText } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Insight } from "@/types/api";
import { SEVERITY_CLASSES, FINDING_STATUS_CLASSES } from "./insights-constants";
import { InsightActions } from "./insight-actions";
import { InsightDetailModal } from "./insight-detail-modal";

const SEVERITY_BORDER: Record<Insight["severity"], string> = {
  critical: "border-l-severity-critical",
  high: "border-l-severity-high",
  medium: "border-l-severity-medium",
  low: "border-l-severity-low",
};

interface InsightCardProps {
  insight: Insight;
  workspaceId: string;
}

export function InsightCard({ insight, workspaceId }: InsightCardProps) {
  const t = useTranslations("insights");
  const [detailOpen, setDetailOpen] = useState(false);

  const TYPE_LABELS: Record<Insight["type"], string> = {
    red_flag: t("typeRedFlag"),
    metric: t("typeMetric"),
    observation: t("typeObservation"),
    missing_info: t("typeMissingInfo"),
  };

  const quote = insight.source_quote
    ? insight.source_quote.slice(0, 100) +
      (insight.source_quote.length > 100 ? "…" : "")
    : null;

  return (
    <>
      <div
        className={cn(
          "vault-card group rounded-lg border border-vault-border bg-vault-surface p-3 space-y-2 text-sm border-l-2 hover:border-vault-border-active transition-all duration-150 cursor-pointer",
          SEVERITY_BORDER[insight.severity],
          insight.status === "rejected" && "opacity-50",
        )}
        onClick={() => setDetailOpen(true)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter") setDetailOpen(true); }}
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={cn(
              "rounded px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide font-medium",
              SEVERITY_CLASSES[insight.severity],
            )}
          >
            {t(
              `severity${insight.severity.charAt(0).toUpperCase() + insight.severity.slice(1)}` as Parameters<
                typeof t
              >[0],
            )}
          </span>
          <span className="rounded bg-vault-border/30 px-2 py-0.5 font-mono text-[11px]">
            {TYPE_LABELS[insight.type]}
          </span>
          <span
            className={cn(
              "ml-auto rounded px-2 py-0.5 text-xs font-medium",
              FINDING_STATUS_CLASSES[insight.status],
            )}
          >
            {t(
              `status${insight.status.charAt(0).toUpperCase() + insight.status.slice(1)}` as Parameters<
                typeof t
              >[0],
            )}
          </span>
        </div>

        <p className="font-medium text-[14px] leading-snug font-reading">{insight.title}</p>
        <p className="line-clamp-2 text-[13px] leading-relaxed text-vault-text-muted font-reading">
          {insight.description}
        </p>

        {quote && (
          <div className="bg-vault-surface-active border-l-2 border-vault-border px-2 py-1.5 rounded flex items-start gap-1.5 text-xs text-vault-text-muted">
            <FileText className="mt-0.5 h-3 w-3 shrink-0" />
            <span className="italic">&ldquo;{quote}&rdquo;</span>
            {insight.source_name && (
              <span className="shrink-0 not-italic">
                — {insight.source_name}
                {insight.source_page ? ` p.${insight.source_page}` : ""}
              </span>
            )}
          </div>
        )}

        <div className="flex items-center gap-2">
          <div className="h-1 flex-1 rounded-full bg-vault-border/30">
            <div
              className="h-1 rounded-full bg-vault-accent transition-all"
              style={{ width: `${insight.confidence_score}%` }}
            />
          </div>
          <span className="text-[11px] tabular-nums text-vault-text-muted font-mono">
            {insight.confidence_score}%
          </span>
          {insight.status === "pending" && (
            <div
              className="md:opacity-0 md:invisible md:group-hover:opacity-100 md:group-hover:visible md:focus-within:opacity-100 md:focus-within:visible transition-all duration-150"
              onClick={(e) => e.stopPropagation()}
            >
              <InsightActions
                insightId={insight.id}
                status={insight.status}
                workspaceId={workspaceId}
              />
            </div>
          )}
        </div>
      </div>

      <InsightDetailModal
        insight={insight}
        workspaceId={workspaceId}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
    </>
  );
}
