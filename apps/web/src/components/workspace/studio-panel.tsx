"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronRight, ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { useInsights } from "@/lib/hooks/use-insights";
import { useNotes } from "@/lib/hooks/use-notes";
import { useEntityStats } from "@/hooks/use-entities";

import { ScanTab } from "./insights/scan-tab";
import { InvestigationsTab } from "./insights/investigations-tab";
import { NotesTab } from "./insights/notes-tab";
import { DeliverablesTab } from "./insights/deliverables-tab";
import { GraphTab } from "./insights/graph-tab";
import { StudioOverview } from "./studio-overview";

export type ViewMode =
  | "overview"
  | "graph"
  | "scan"
  | "investigations"
  | "notes"
  | "rapport"
  | "synthese"
  | "matrice";

interface StudioPanelProps {
  workspaceId: string;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

const TABS: { id: ViewMode; labelKey: string }[] = [
  { id: "overview", labelKey: "tabs.studio" },
  { id: "graph", labelKey: "tabs.graph" },
  { id: "notes", labelKey: "tabs.notes" },
  { id: "scan", labelKey: "tabs.scan" },
  { id: "investigations", labelKey: "tabs.investigations" },
];

const SEVERITY_COLORS = {
  critical: "bg-vault-danger",
  high: "bg-vault-warning",
  medium: "bg-vault-medium",
  low: "bg-vault-low",
} as const;

export function StudioPanel({
  workspaceId,
  collapsed,
  onToggleCollapse,
}: StudioPanelProps) {
  const t = useTranslations("studio");
  const [activeView, setActiveView] = useState<ViewMode>("overview");
  const { data: insightsData } = useInsights(workspaceId, {});
  const insights = insightsData?.data ?? [];
  const { data: notesData } = useNotes(workspaceId);
  const notesCount = notesData?.data?.length ?? 0;
  const { data: entityStats } = useEntityStats(workspaceId);
  const entityCount = entityStats?.total_entities ?? 0;

  const severityCounts = insights.reduce(
    (acc, f) => {
      acc[f.severity] = (acc[f.severity] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  if (collapsed) {
    return (
      <div className="h-full w-full flex flex-col items-center overflow-hidden py-4 bg-vault-bg border-l border-vault-border">
        <button
          onClick={onToggleCollapse}
          className="mb-4 p-1.5 rounded hover:bg-vault-surface-hover transition-colors"
        >
          <ChevronRight className="h-4 w-4 text-vault-text-muted rotate-180" />
        </button>
        <span className="font-mono text-[11px] tracking-widest text-vault-text-muted uppercase [writing-mode:vertical-lr] mb-4">
          {t("label")}
        </span>
        <div className="flex flex-col gap-1.5 mt-2">
          {(["critical", "high", "medium", "low"] as const).map((sev) =>
            severityCounts[sev] ? (
              <div
                key={sev}
                className={cn(
                  "h-5 w-5 flex items-center justify-center rounded text-[11px] font-mono text-white",
                  SEVERITY_COLORS[sev],
                )}
              >
                {severityCounts[sev]}
              </div>
            ) : null,
          )}
        </div>
      </div>
    );
  }

  const insightsCount = insights.length;
  const isTabView = TABS.some((tab) => tab.id === activeView);
  const showBackButton = activeView !== "overview" && !isTabView;

  function renderContent() {
    switch (activeView) {
      case "overview":
        return <StudioOverview workspaceId={workspaceId} onSelect={setActiveView} />;
      case "graph":
        return <GraphTab workspaceId={workspaceId} />;
      case "scan":
        return <ScanTab workspaceId={workspaceId} />;
      case "investigations":
        return <InvestigationsTab workspaceId={workspaceId} />;
      case "notes":
        return <NotesTab workspaceId={workspaceId} />;
      case "rapport":
      case "synthese":
      case "matrice":
        return <DeliverablesTab workspaceId={workspaceId} />;
      default:
        return <StudioOverview workspaceId={workspaceId} onSelect={setActiveView} />;
    }
  }

  return (
    <div className="h-full flex flex-col bg-vault-bg">
      {/* Tab bar */}
      <div className="flex items-center h-11 px-2 border-b border-vault-border bg-vault-surface shrink-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveView(tab.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 h-full text-[13px] border-b-2 transition-colors",
              activeView === tab.id || (showBackButton && tab.id === "overview")
                ? "text-vault-text border-vault-accent"
                : "text-vault-text-muted border-transparent hover:text-vault-text-secondary",
            )}
          >
            {t(tab.labelKey)}
            {tab.id === "notes" && notesCount > 0 && (
              <span className="font-mono text-[11px] px-1 py-0.5 rounded bg-purple-500/15 text-purple-400">
                {notesCount}
              </span>
            )}
            {tab.id === "scan" && insightsCount > 0 && (
              <span className="font-mono text-[11px] px-1 py-0.5 rounded bg-vault-accent-dim text-vault-accent">
                {insightsCount}
              </span>
            )}
            {tab.id === "graph" && entityCount > 0 && (
              <span className="font-mono text-[11px] px-1 py-0.5 rounded bg-blue-500/15 text-blue-400">
                {entityCount}
              </span>
            )}
          </button>
        ))}
        <button
          onClick={onToggleCollapse}
          className="ml-auto p-1.5 rounded hover:bg-vault-surface-hover transition-colors"
        >
          <ChevronRight className="h-4 w-4 text-vault-text-muted" />
        </button>
      </div>

      {/* Back button for generate views */}
      {showBackButton && (
        <div className="flex items-center gap-2 px-4 py-2 border-b border-vault-border shrink-0">
          <button
            onClick={() => setActiveView("overview")}
            className="flex items-center gap-1.5 text-[13px] text-vault-text-muted hover:text-vault-text-secondary transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {t("backToStudio")}
          </button>
        </div>
      )}

      {/* Content */}
      <div
        key={activeView}
        className="flex-1 flex flex-col min-h-0 overflow-auto tab-crossfade"
      >
        {renderContent()}
      </div>
    </div>
  );
}
