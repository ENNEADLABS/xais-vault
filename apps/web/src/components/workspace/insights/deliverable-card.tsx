"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download, AlertTriangle, Loader2, Eye, EyeOff } from "lucide-react";
import { cn, formatFileSize, formatRelativeDate } from "@/lib/utils";
import { API_URL } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";
import type { Deliverable } from "@/types/api";

const TYPE_CLASSES: Record<Deliverable["type"], string> = {
  executive_summary: "bg-purple-900/30 text-purple-400",
  investment_memo: "bg-vault-accent/15 text-vault-accent",
  dd_report: "bg-teal-900/30 text-teal-400",
};

const TYPE_LABELS: Record<Deliverable["type"], string> = {
  executive_summary: "Exec Summary",
  investment_memo: "Memo",
  dd_report: "DD Report",
};

const STATUS_CLASSES: Record<Deliverable["status"], string> = {
  pending: "bg-vault-medium-dim text-vault-medium",
  processing: "bg-vault-accent-dim text-vault-accent animate-pulse",
  completed: "bg-vault-success-dim text-vault-success",
  failed: "bg-vault-danger-dim text-vault-danger",
};

interface DeliverableCardProps {
  deliverable: Deliverable;
}

export function DeliverableCard({ deliverable: del }: DeliverableCardProps) {
  const t = useTranslations("deliverables");
  const locale = useLocale();
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  async function handleDownload() {
    setDownloading(true);
    setDownloadError(false);
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      const headers: HeadersInit = {};
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }

      const res = await fetch(
        `${API_URL}/api/v2/workspaces/${del.workspace_id}/deliverables/${del.id}/download`,
        { headers },
      );

      if (!res.ok) throw new Error("Download failed");

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${del.name}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setDownloadError(true);
    } finally {
      setDownloading(false);
    }
  }

  const STATUS_LABELS: Record<Deliverable["status"], string> = {
    pending: t("statusPending"),
    processing: t("statusProcessing"),
    completed: t("statusCompleted"),
    failed: t("statusFailed"),
  };

  const hasPreview = del.status === "completed" && del.content_markdown;

  return (
    <div className="vault-card rounded-lg border border-vault-border bg-vault-surface p-3 space-y-2 text-sm">
      <div className="flex items-center gap-2 flex-wrap">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            TYPE_CLASSES[del.type],
          )}
        >
          {TYPE_LABELS[del.type]}
        </span>
        <span
          className={cn(
            "ml-auto rounded-full px-2 py-0.5 text-xs font-medium",
            STATUS_CLASSES[del.status],
          )}
        >
          {STATUS_LABELS[del.status]}
        </span>
      </div>

      <p className="font-medium text-[14px] leading-snug font-reading">{del.name}</p>

      {del.status === "processing" && (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="h-1.5 flex-1 rounded-full bg-muted">
              <div
                className="h-1.5 rounded-full bg-vault-accent transition-all"
                style={{ width: `${del.progress_percent}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {del.progress_percent}%
            </span>
          </div>
          {del.current_step && (
            <p className="text-xs text-muted-foreground">
              {t("step", { step: del.current_step })}
            </p>
          )}
        </div>
      )}

      {del.status === "completed" && (
        <div className="flex items-center justify-between">
          {del.file_size_bytes && (
            <span className="text-xs text-muted-foreground">
              {t("fileSize", { size: formatFileSize(del.file_size_bytes) })}
            </span>
          )}
          <div className="flex items-center gap-1">
            {hasPreview && (
              <Button
                variant="ghost"
                size="sm"
                className="text-vault-text-muted hover:text-vault-text hover:bg-vault-surface-hover"
                onClick={() => setShowPreview(!showPreview)}
              >
                {showPreview
                  ? <EyeOff className="h-3.5 w-3.5 mr-1" />
                  : <Eye className="h-3.5 w-3.5 mr-1" />}
                {showPreview ? t("closePreview") : t("preview")}
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="text-vault-accent hover:text-vault-accent/80 hover:bg-vault-accent/10"
              onClick={() => void handleDownload()}
              disabled={downloading}
            >
              {downloading
                ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                : <Download className="h-3.5 w-3.5 mr-1" />}
              {t("download")}
            </Button>
          </div>
        </div>
      )}

      {/* Preview Markdown inline */}
      {showPreview && del.content_markdown && (
        <div className="mt-2 rounded-lg border border-vault-border bg-vault-bg p-3 max-h-80 overflow-y-auto">
          <div className="prose prose-sm prose-invert max-w-none text-[12px] leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {del.content_markdown}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {downloadError && (
        <p className="text-xs text-destructive">{t("downloadError")}</p>
      )}

      {del.status === "failed" && del.error_message && (
        <div className="flex items-start gap-1.5 text-xs text-destructive">
          <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
          <span>{del.error_message}</span>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        {t("createdAgo", { time: formatRelativeDate(del.created_at, locale) })}
      </p>
    </div>
  );
}
