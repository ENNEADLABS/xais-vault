"use client";

import { useTranslations } from "next-intl";
import { FileText, AlertTriangle, StickyNote, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { WorkspaceScore } from "./workspace-score";
import { AnalyzeButton } from "./analyze-button";
import type { ViewMode } from "./studio-panel";
import type {
  Insight,
  Investigation,
  Deliverable,
  Source,
  Note,
} from "@/types/api";

interface DossierSummaryProps {
  workspaceId: string;
  scanStatus: string;
  sources: Source[];
  insights: Insight[];
  investigations: Investigation[];
  deliverables: Deliverable[];
  notes: Note[];
  onSelect: (view: ViewMode) => void;
}

interface KpiTile {
  id: ViewMode;
  icon: React.ElementType;
  value: string;
  label: string;
  accent?: string;
  visible: boolean;
}

export function DossierSummary({
  workspaceId,
  scanStatus,
  sources,
  insights,
  investigations,
  deliverables,
  notes,
  onSelect,
}: DossierSummaryProps) {
  const t = useTranslations("studio.summary");

  const readyCount = sources.filter((s) => s.status === "ready").length;
  const criticalCount = insights.filter(
    (f) => f.severity === "critical",
  ).length;
  const highCount = insights.filter((f) => f.severity === "high").length;
  const pinnedCount = notes.filter((n) => n.is_pinned).length;
  const completedInv = investigations.filter(
    (i) => i.status === "completed",
  ).length;

  const tiles: KpiTile[] = [
    {
      id: "scan",
      icon: FileText,
      value: `${readyCount}/${sources.length}`,
      label: t("sourcesReady"),
      visible: sources.length > 0,
    },
    {
      id: "scan",
      icon: AlertTriangle,
      value: String(insights.length),
      label:
        criticalCount > 0
          ? t("insightsCritical", { count: criticalCount })
          : highCount > 0
            ? t("insightsHigh", { count: highCount })
            : t("insights"),
      accent:
        criticalCount > 0
          ? "text-red-400"
          : highCount > 0
            ? "text-orange-400"
            : undefined,
      visible: insights.length > 0,
    },
    {
      id: "notes",
      icon: StickyNote,
      value: String(notes.length),
      label:
        pinnedCount > 0 ? t("notesPinned", { count: pinnedCount }) : t("notes"),
      visible: true,
    },
    {
      id: "investigations",
      icon: Search,
      value: `${completedInv}/${investigations.length}`,
      label: t("investigationsCompleted"),
      visible: investigations.length > 0,
    },
  ];

  const visibleTiles = tiles.filter((t) => t.visible);

  return (
    <div className="vault-card flex items-center gap-3 rounded-xl border border-vault-border bg-vault-surface p-3">
      {/* Workspace Score compact */}
      <button
        onClick={() => onSelect("scan")}
        className="shrink-0 hover:opacity-80 transition-opacity"
      >
        <WorkspaceScore
          insights={insights}
          investigations={investigations}
          deliverables={deliverables}
          size="sm"
        />
      </button>

      {/* DD Launch Button — visible si pas encore scanné */}
      {scanStatus !== "scanned" && sources.length > 0 && (
        <AnalyzeButton workspaceId={workspaceId} scanStatus={scanStatus} />
      )}

      {/* Séparateur */}
      <div className="h-8 w-px bg-vault-border/50 shrink-0" />

      {/* KPI tiles */}
      <div className="flex flex-1 items-center gap-3 overflow-x-auto">
        {visibleTiles.map((tile, i) => (
          <button
            key={`${tile.id}-${i}`}
            onClick={() => onSelect(tile.id)}
            className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-vault-surface-hover transition-colors shrink-0"
          >
            <tile.icon
              className={cn("h-3.5 w-3.5 text-vault-text-muted", tile.accent)}
            />
            <div className="text-left">
              <span
                className={cn(
                  "font-mono text-sm font-semibold",
                  tile.accent || "text-vault-text",
                )}
              >
                {tile.value}
              </span>
              <span className="ml-1.5 text-[11px] text-vault-text-muted">
                {tile.label}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
