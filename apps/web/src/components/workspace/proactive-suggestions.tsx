"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { X, Scan, AlertTriangle, Search, FileOutput, StickyNote } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ViewMode } from "./studio-panel";
import type { Insight, Investigation, Deliverable, Source, Note } from "@/types/api";

interface ProactiveSuggestionsProps {
  sources: Source[];
  insights: Insight[];
  investigations: Investigation[];
  deliverables: Deliverable[];
  notes: Note[];
  scanStatus: string;
  onSelect: (view: ViewMode) => void;
}

interface Suggestion {
  key: string;
  icon: React.ElementType;
  message: string;
  action: string;
  target: ViewMode;
  color: string;
}

export function ProactiveSuggestions({
  sources,
  insights,
  investigations,
  deliverables,
  notes,
  scanStatus,
  onSelect,
}: ProactiveSuggestionsProps) {
  const t = useTranslations("studio.suggestions");
  const [dismissed, setDismissed] = useState<string | null>(null);

  const readyCount = sources.filter((s) => s.status === "ready").length;
  const criticalPending = insights.filter(
    (f) => f.severity === "critical" && f.status === "pending",
  ).length;
  const confirmedNoInv = insights.filter(
    (f) => f.status === "confirmed",
  ).length;
  const completedInv = investigations.filter((i) => i.status === "completed").length;

  // Suggestions ordonnées par priorité (la première matche gagne)
  const suggestions: Suggestion[] = [];

  if (readyCount > 0 && scanStatus === "pending") {
    suggestions.push({
      key: "scan",
      icon: Scan,
      message: t("scanReady"),
      action: t("scanAction"),
      target: "scan",
      color: "border-blue-500/30 bg-blue-500/5",
    });
  }

  if (criticalPending > 0) {
    suggestions.push({
      key: "critical",
      icon: AlertTriangle,
      message: t("criticalPending", { count: criticalPending }),
      action: t("criticalAction"),
      target: "scan",
      color: "border-red-500/30 bg-red-500/5",
    });
  }

  if (confirmedNoInv > 0 && investigations.length === 0) {
    suggestions.push({
      key: "investigate",
      icon: Search,
      message: t("investigateReady"),
      action: t("investigateAction"),
      target: "scan",
      color: "border-amber-500/30 bg-amber-500/5",
    });
  }

  if (completedInv > 0 && deliverables.length === 0) {
    suggestions.push({
      key: "deliverable",
      icon: FileOutput,
      message: t("generateReady"),
      action: t("generateAction"),
      target: "rapport",
      color: "border-green-500/30 bg-green-500/5",
    });
  }

  if (notes.length === 0 && insights.length > 0) {
    suggestions.push({
      key: "notes",
      icon: StickyNote,
      message: t("addNotes"),
      action: t("addNotesAction"),
      target: "notes",
      color: "border-purple-500/30 bg-purple-500/5",
    });
  }

  // Afficher la première suggestion non dismissée
  const active = suggestions.find((s) => s.key !== dismissed);
  if (!active) return null;

  return (
    <div className={cn("flex items-center gap-3 rounded-lg border p-3", active.color)}>
      <active.icon className="h-4 w-4 shrink-0 text-vault-text-secondary" />
      <p className="flex-1 text-[12px] text-vault-text-secondary">{active.message}</p>
      <button
        onClick={() => onSelect(active.target)}
        className="shrink-0 rounded-md bg-vault-surface px-2.5 py-1 text-[11px] font-medium text-vault-text hover:bg-vault-surface-hover transition-colors border border-vault-border"
      >
        {active.action}
      </button>
      <button
        onClick={() => setDismissed(active.key)}
        className="shrink-0 p-0.5 text-vault-text-muted hover:text-vault-text transition-colors"
        aria-label="Dismiss"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
