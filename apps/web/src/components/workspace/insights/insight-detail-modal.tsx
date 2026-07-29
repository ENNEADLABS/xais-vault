"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FileText, Plus } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useUpdateInsight } from "@/lib/hooks/use-insights";
import { useNotes } from "@/lib/hooks/use-notes";
import type { Insight } from "@/types/api";
import { NoteCard } from "./note-card";
import { NoteEditor } from "./note-editor";
import { InvestigationForm } from "./investigation-form";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400",
  high: "bg-orange-500/15 text-orange-400",
  medium: "bg-amber-500/15 text-amber-400",
  low: "bg-green-500/15 text-green-400",
};

const TYPE_LABELS: Record<string, string> = {
  red_flag: "Red Flag",
  metric: "Metric",
  observation: "Observation",
  missing_info: "Missing Info",
};

interface InsightDetailModalProps {
  insight: Insight;
  workspaceId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function InsightDetailModal({
  insight,
  workspaceId,
  open,
  onOpenChange,
}: InsightDetailModalProps) {
  const t = useTranslations("insightDetail");
  const updateInsight = useUpdateInsight(workspaceId);
  const { data: notesData } = useNotes(workspaceId);
  const [creatingNote, setCreatingNote] = useState(false);

  const linkedNotes = (notesData?.data ?? []).filter(
    (n) => n.linked_insight_id === insight.id,
  );
  const isPending = insight.status === "pending";
  const canInvestigate = insight.status !== "rejected";

  function handleAction(status: "confirmed" | "rejected" | "investigating") {
    updateInsight.mutate(
      { insightId: insight.id, update: { status } },
      {
        onSuccess: () => {
          toast.success(t(`${status}Toast`));
          if (status !== "investigating") onOpenChange(false);
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn("rounded px-1.5 py-0.5 text-[11px] font-mono uppercase", SEVERITY_COLORS[insight.severity])}>
              {insight.severity}
            </span>
            <span className="rounded bg-vault-border/30 px-1.5 py-0.5 text-[11px] font-mono uppercase text-vault-text-secondary">
              {TYPE_LABELS[insight.type] ?? insight.type}
            </span>
            <span className="rounded bg-vault-border/20 px-1.5 py-0.5 text-[11px] font-mono uppercase text-vault-text-muted">
              {insight.status}
            </span>
          </div>
          <DialogTitle className="text-sm font-semibold mt-1">
            {insight.title}
          </DialogTitle>
        </DialogHeader>

        {/* Description complète */}
        <p className="text-[13px] leading-relaxed text-vault-text-secondary whitespace-pre-wrap">
          {insight.description}
        </p>

        {/* Citation source */}
        {insight.source_quote && (
          <div className="rounded-lg border border-vault-border/50 bg-vault-bg p-3">
            <p className="text-[12px] italic text-vault-text-secondary leading-relaxed">
              &ldquo;{insight.source_quote}&rdquo;
            </p>
            {insight.source_name && (
              <p className="mt-1.5 flex items-center gap-1.5 text-[11px] text-vault-text-muted">
                <FileText className="h-3 w-3" />
                {insight.source_name}
                {insight.source_page && ` p.${insight.source_page}`}
                {insight.source_section && ` — ${insight.source_section}`}
              </p>
            )}
          </div>
        )}

        {/* Score de confiance */}
        {insight.confidence_score != null && (
          <div className="space-y-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-vault-text-muted">
              {t("confidence")}
            </span>
            <div className="flex items-center gap-2">
              <div className="h-1.5 flex-1 rounded-full bg-vault-border/30">
                <div
                  className="h-1.5 rounded-full bg-vault-accent transition-all"
                  style={{ width: `${insight.confidence_score}%` }}
                />
              </div>
              <span className="font-mono text-xs text-vault-text-secondary">
                {insight.confidence_score}%
              </span>
            </div>
          </div>
        )}

        {/* Actions */}
        {isPending && (
          <div className="flex gap-2 pt-1">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => handleAction("confirmed")}
              disabled={updateInsight.isPending}
            >
              {t("confirm")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs text-red-400 hover:text-red-300"
              onClick={() => handleAction("rejected")}
              disabled={updateInsight.isPending}
            >
              {t("reject")}
            </Button>
          </div>
        )}

        {/* Investigation custom */}
        {canInvestigate && (
          <div className="space-y-2 border-t border-vault-border/30 pt-3">
            <h4 className="text-[11px] font-mono uppercase tracking-wider text-vault-text-muted">
              {t("investigation.title")}
            </h4>
            <InvestigationForm workspaceId={workspaceId} insightId={insight.id} />
          </div>
        )}

        {/* Notes liées */}
        <div className="space-y-2 border-t border-vault-border/30 pt-3">
          <div className="flex items-center justify-between">
            <h4 className="text-[11px] font-mono uppercase tracking-wider text-vault-text-muted">
              {t("linkedNotes", { count: linkedNotes.length })}
            </h4>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 gap-1 text-xs"
              onClick={() => setCreatingNote(true)}
            >
              <Plus className="h-3 w-3" />
              {t("addNote")}
            </Button>
          </div>

          {creatingNote && (
            <NoteEditor
              workspaceId={workspaceId}
              linkedInsightId={insight.id}
              onClose={() => setCreatingNote(false)}
            />
          )}

          {linkedNotes.map((note) => (
            <NoteCard key={note.id} note={note} workspaceId={workspaceId} />
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
