"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { SearchX } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { useInsights, type InsightsFilters } from "@/lib/hooks/use-insights";
import { ScanStatusHeader } from "./scan-status-header";
import { InsightsToolbar } from "./insights-toolbar";
import { InsightCard } from "./insight-card";
import { InsightCardSkeleton } from "./insight-card-skeleton";
import { SeverityCounters } from "./severity-counters";
import type { Insight } from "@/types/api";

// ─── Tri côté frontend ───────────────────────────────────

type SortKey = "severity" | "confidence" | "date" | "type";

const SEVERITY_ORDER: Record<Insight["severity"], number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function sortInsights(insights: Insight[], sortBy: SortKey): Insight[] {
  const sorted = [...insights];
  switch (sortBy) {
    case "severity":
      sorted.sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
      break;
    case "confidence":
      sorted.sort((a, b) => b.confidence_score - a.confidence_score);
      break;
    case "date":
      sorted.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
      break;
    case "type":
      sorted.sort((a, b) => a.type.localeCompare(b.type));
      break;
  }
  return sorted;
}

// ─── Composant ───────────────────────────────────────────

interface ScanTabProps {
  workspaceId: string;
}

export function ScanTab({ workspaceId }: ScanTabProps) {
  const t = useTranslations("insights");
  const [filters, setFilters] = useState<InsightsFilters>({});
  const [sortBy, setSortBy] = useState<SortKey>("severity");
  const { data, isLoading } = useInsights(workspaceId, filters);
  const insights = data?.data ?? [];

  const sortedInsights = useMemo(
    () => sortInsights(insights, sortBy),
    [insights, sortBy],
  );

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <ScanStatusHeader workspaceId={workspaceId} insightsCount={insights.length} />

      {/* Severity counters */}
      {!isLoading && insights.length > 0 && (
        <div className="px-3 py-2 border-b border-vault-border">
          <SeverityCounters insights={insights} />
        </div>
      )}

      {/* Toolbar filtres + tri */}
      <InsightsToolbar filters={filters} onFiltersChange={setFilters}>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as SortKey)}
          className="ml-auto h-7 rounded border border-vault-border bg-vault-surface px-2 text-xs text-vault-text-muted focus:outline-none"
        >
          <option value="severity">{t("sortSeverity")}</option>
          <option value="confidence">{t("sortConfidence")}</option>
          <option value="date">{t("sortDate")}</option>
          <option value="type">{t("sortType")}</option>
        </select>
      </InsightsToolbar>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {isLoading ? (
          <>
            <InsightCardSkeleton />
            <InsightCardSkeleton />
            <InsightCardSkeleton />
          </>
        ) : sortedInsights.length === 0 ? (
          <EmptyState
            icon={SearchX}
            title={t("noInsights")}
            description={t("noInsightsHint")}
            label="NO_FINDINGS"
          />
        ) : (
          sortedInsights.map((insight) => (
            <InsightCard key={insight.id} insight={insight} workspaceId={workspaceId} />
          ))
        )}
      </div>
    </div>
  );
}
