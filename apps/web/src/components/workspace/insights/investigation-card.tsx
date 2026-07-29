"use client";

import { useTranslations } from "next-intl";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ExternalLink, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Investigation } from "@/types/api";
import { INVESTIGATION_STATUS_CLASSES } from "./insights-constants";

interface InvestigationCardProps {
  investigation: Investigation;
}

export function InvestigationCard({
  investigation: inv,
}: InvestigationCardProps) {
  const t = useTranslations("investigations");

  const SCOPE_LABELS: Record<Investigation["scope"], string> = {
    documents: t("scopeDocuments"),
    web: t("scopeWeb"),
    both: t("scopeBoth"),
  };

  const STATUS_LABELS: Record<Investigation["status"], string> = {
    pending: t("statusPending"),
    processing: t("statusProcessing"),
    completed: t("statusCompleted"),
    failed: t("statusFailed"),
  };

  const duration =
    inv.started_at && inv.completed_at
      ? Math.round(
          (new Date(inv.completed_at).getTime() -
            new Date(inv.started_at).getTime()) /
            1000,
        )
      : null;

  return (
    <div className="rounded-lg border border-vault-border bg-vault-surface p-3 space-y-2 text-sm">
      <div className="flex items-center gap-2 flex-wrap">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            INVESTIGATION_STATUS_CLASSES[inv.status],
          )}
        >
          {STATUS_LABELS[inv.status]}
        </span>
        <span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
          {SCOPE_LABELS[inv.scope]}
        </span>
        {duration !== null && (
          <span className="ml-auto text-xs text-muted-foreground">
            {t("duration", { duration: `${duration}s` })}
          </span>
        )}
      </div>

      <p className="font-medium text-sm leading-snug">{inv.question}</p>

      {inv.status === "pending" && (
        <p className="text-xs text-muted-foreground italic">
          {t("statusPending")}…
        </p>
      )}

      {inv.status === "processing" && (
        <div className="space-y-1.5 animate-pulse">
          <div className="h-2 w-full rounded bg-muted" />
          <div className="h-2 w-4/5 rounded bg-muted" />
          <div className="h-2 w-3/5 rounded bg-muted" />
        </div>
      )}

      {inv.status === "failed" && (
        <p className="text-xs text-destructive">{t("statusFailed")}</p>
      )}

      {inv.status === "completed" && inv.report && (
        <div className="prose prose-sm dark:prose-invert max-w-none border-t border-vault-border/50 pt-2">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {inv.report}
          </ReactMarkdown>
        </div>
      )}

      {inv.web_sources && inv.web_sources.length > 0 && (
        <div className="space-y-1 border-t border-vault-border/50 pt-2">
          <p className="text-xs font-medium text-muted-foreground">
            {t("webSources")}
          </p>
          <div className="flex flex-wrap gap-1">
            {inv.web_sources.map((src) => (
              <a
                key={src.url}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                <ExternalLink className="h-3 w-3" />
                {src.title}
              </a>
            ))}
          </div>
        </div>
      )}

      {inv.doc_references && inv.doc_references.length > 0 && (
        <div className="space-y-1 border-t border-vault-border/50 pt-2">
          <p className="text-xs font-medium text-muted-foreground">
            {t("docReferences")}
          </p>
          {inv.doc_references.map((ref, i) => (
            <div
              key={i}
              className="flex items-start gap-1.5 text-xs text-muted-foreground"
            >
              <FileText className="mt-0.5 h-3 w-3 shrink-0" />
              <span>
                p.{ref.page} —{" "}
                <span className="italic">
                  &ldquo;{ref.quote.slice(0, 80)}
                  {ref.quote.length > 80 ? "…" : ""}&rdquo;
                </span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
