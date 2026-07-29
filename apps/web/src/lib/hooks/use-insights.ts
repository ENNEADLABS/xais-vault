"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ApiResponse } from "@/lib/api";
import type { Insight } from "@/types/api";

interface InsightsFilters {
  type?: Insight["type"] | null;
  severity?: Insight["severity"] | null;
  status?: Insight["status"] | null;
}

export type { InsightsFilters };

export function useInsights(workspaceId: string, filters: InsightsFilters = {}) {
  const params = new URLSearchParams();
  if (filters.type) params.set("type", filters.type);
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.status) params.set("status", filters.status);
  const qs = params.toString();

  return useQuery({
    queryKey: ["insights", workspaceId, filters],
    queryFn: () =>
      api.get<ApiResponse<Insight[]>>(
        `/workspaces/${workspaceId}/insights/${qs ? `?${qs}` : ""}`,
      ),
    enabled: !!workspaceId,
  });
}

const STATUS_TO_ACTION: Record<string, string> = {
  confirmed: "confirm",
  rejected: "reject",
  investigating: "investigate",
};

export function useUpdateInsight(workspaceId: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      insightId,
      update,
    }: {
      insightId: string;
      update: { status: Insight["status"] };
    }) =>
      api.patch<ApiResponse<Insight>>(
        `/workspaces/${workspaceId}/insights/${insightId}`,
        { action: STATUS_TO_ACTION[update.status] ?? update.status },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["insights", workspaceId] });
    },
  });
}
