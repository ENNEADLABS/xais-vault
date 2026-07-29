"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { InsightsFilters } from "@/lib/hooks/use-insights";

interface InsightsToolbarProps {
  filters: InsightsFilters;
  onFiltersChange: (filters: InsightsFilters) => void;
  children?: ReactNode;
}

export function InsightsToolbar({
  filters,
  onFiltersChange,
  children,
}: InsightsToolbarProps) {
  const t = useTranslations("insights");

  function handleSeverity(value: string | null) {
    onFiltersChange({
      ...filters,
      severity:
        !value || value === "all"
          ? null
          : (value as InsightsFilters["severity"]),
    });
  }

  function handleStatus(value: string | null) {
    onFiltersChange({
      ...filters,
      status:
        !value || value === "all" ? null : (value as InsightsFilters["status"]),
    });
  }

  return (
    <div className="flex gap-2 border-b px-3 py-2">
      <Select value={filters.severity ?? "all"} onValueChange={handleSeverity}>
        <SelectTrigger size="sm" className="h-7 text-xs">
          <SelectValue placeholder={t("filterSeverity")} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{t("filterAll")}</SelectItem>
          <SelectItem value="critical">{t("severityCritical")}</SelectItem>
          <SelectItem value="high">{t("severityHigh")}</SelectItem>
          <SelectItem value="medium">{t("severityMedium")}</SelectItem>
          <SelectItem value="low">{t("severityLow")}</SelectItem>
        </SelectContent>
      </Select>

      <Select value={filters.status ?? "all"} onValueChange={handleStatus}>
        <SelectTrigger size="sm" className="h-7 text-xs">
          <SelectValue placeholder={t("filterStatus")} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{t("filterAll")}</SelectItem>
          <SelectItem value="pending">{t("statusPending")}</SelectItem>
          <SelectItem value="confirmed">{t("statusConfirmed")}</SelectItem>
          <SelectItem value="rejected">{t("statusRejected")}</SelectItem>
          <SelectItem value="investigating">
            {t("statusInvestigating")}
          </SelectItem>
        </SelectContent>
      </Select>

      {children}
    </div>
  );
}
