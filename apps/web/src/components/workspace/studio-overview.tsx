"use client";

import { useTranslations } from "next-intl";
import { FileText, ClipboardList, Grid3X3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useInsights } from "@/lib/hooks/use-insights";
import { useInvestigations } from "@/lib/hooks/use-investigations";
import { useNotes } from "@/lib/hooks/use-notes";
import { useDeliverables } from "@/lib/hooks/use-deliverables";
import { useSources } from "@/lib/hooks/use-sources";
import { useWorkspace } from "@/lib/hooks/use-workspace";
import { DossierSummary } from "./dossier-summary";
import { ProactiveSuggestions } from "./proactive-suggestions";
import { SuggestedQuestionsBlock } from "./suggested-questions-block";
import { SeverityCounters } from "./insights/severity-counters";
import { ActivityTimeline } from "./activity-timeline";
import type { ViewMode } from "./studio-panel";

interface StudioOverviewProps {
  workspaceId: string;
  onSelect: (view: ViewMode) => void;
}

export function StudioOverview({ workspaceId, onSelect }: StudioOverviewProps) {
  const t = useTranslations("studio");
  const { data: insightsData } = useInsights(workspaceId, {});
  const { data: invData } = useInvestigations(workspaceId);
  const { data: notesData } = useNotes(workspaceId);
  const { data: delData } = useDeliverables(workspaceId);
  const { data: srcData } = useSources(workspaceId);
  const { data: workspaceData } = useWorkspace(workspaceId);

  const insights = insightsData?.data ?? [];
  const investigations = invData?.data ?? [];
  const notes = notesData?.data ?? [];
  const deliverables = delData?.data ?? [];
  const sources = srcData?.data ?? [];
  const scanStatus = workspaceData?.data?.scan_status ?? "pending";

  const rapportDel = deliverables.find((d) => d.type === "dd_report");
  const syntheseDel = deliverables.find((d) => d.type === "executive_summary");
  const matriceDel = deliverables.find((d) => d.type === "investment_memo");

  const generateTiles = [
    {
      id: "rapport" as ViewMode,
      icon: FileText,
      title: t("tiles.rapport"),
      done: !!rapportDel,
    },
    {
      id: "synthese" as ViewMode,
      icon: ClipboardList,
      title: t("tiles.synthese"),
      done: !!syntheseDel,
    },
    {
      id: "matrice" as ViewMode,
      icon: Grid3X3,
      title: t("tiles.matrice"),
      done: !!matriceDel,
    },
  ];

  return (
    <div className="p-4 space-y-4">
      {/* ─── Dossier Summary — KPIs compacts ─── */}
      <DossierSummary
        workspaceId={workspaceId}
        scanStatus={scanStatus}
        sources={sources}
        insights={insights}
        investigations={investigations}
        deliverables={deliverables}
        notes={notes}
        onSelect={onSelect}
      />

      {/* ─── Suggestions proactives ─── */}
      <ProactiveSuggestions
        sources={sources}
        insights={insights}
        investigations={investigations}
        deliverables={deliverables}
        notes={notes}
        scanStatus={scanStatus}
        onSelect={onSelect}
      />

      {/* ─── Questions à explorer (pré-calculées) ─── */}
      <SuggestedQuestionsBlock workspaceId={workspaceId} />

      {/* ─── Risk Distribution ─── */}
      {insights.length > 0 && (
        <div className="vault-card rounded-xl border border-vault-border bg-vault-surface p-4">
          <h3 className="text-[12px] font-mono uppercase tracking-wider text-vault-text-muted mb-3">
            {t("riskDistribution")}
          </h3>
          <SeverityCounters insights={insights} />
          <div className="mt-3 flex gap-0.5 h-2 rounded-full overflow-hidden bg-vault-bg">
            {(["critical", "high", "medium", "low"] as const).map((sev) => {
              const count = insights.filter((f) => f.severity === sev).length;
              if (count === 0) return null;
              const pct = (count / insights.length) * 100;
              const colors: Record<string, string> = {
                critical: "bg-vault-danger",
                high: "bg-vault-warning",
                medium: "bg-vault-medium",
                low: "bg-vault-low",
              };
              return (
                <div
                  key={sev}
                  className={cn("h-full transition-all", colors[sev])}
                  style={{ width: `${pct}%` }}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* ─── Activité récente ─── */}
      <div className="vault-card rounded-xl border border-vault-border bg-vault-surface p-4">
        <h3 className="text-[12px] font-mono uppercase tracking-wider text-vault-text-muted mb-3">
          {t("recentActivity")}
        </h3>
        <ActivityTimeline
          sources={sources}
          insights={insights}
          investigations={investigations}
          deliverables={deliverables}
          notes={notes}
          maxItems={5}
        />
        {sources.length === 0 && insights.length === 0 && (
          <p className="text-[12px] text-vault-text-muted">
            {t("uploadToStart")}
          </p>
        )}
      </div>

      {/* ─── Générer ─── */}
      <div className="vault-card rounded-xl border border-vault-border bg-vault-surface p-4">
        <h3 className="text-[12px] font-mono uppercase tracking-wider text-vault-text-muted mb-3">
          {t("generateSection")}
        </h3>
        <div className="grid grid-cols-3 gap-2">
          {generateTiles.map((tile) => (
            <button
              key={tile.id}
              onClick={() => onSelect(tile.id)}
              className={cn(
                "flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-all text-center",
                tile.done
                  ? "bg-vault-surface border-vault-border hover:border-vault-border-active"
                  : "bg-vault-bg border-vault-border hover:border-vault-border-active hover:bg-vault-surface opacity-80 hover:opacity-100",
              )}
            >
              <tile.icon className="h-5 w-5 text-vault-text-muted" />
              <span className="text-[11px] font-medium text-vault-text-secondary leading-tight">
                {tile.title}
              </span>
              {tile.done ? (
                <span className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-vault-success" />
                  <span className="text-[10px] text-vault-success">
                    {t("tiles.ready")}
                  </span>
                </span>
              ) : (
                <span className="text-[10px] font-mono text-vault-accent">
                  {t("tiles.generate")}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
