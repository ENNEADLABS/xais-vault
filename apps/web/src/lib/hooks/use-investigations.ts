"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ApiResponse } from "@/lib/api";
import type { Investigation } from "@/types/api";

export function useInvestigations(workspaceId: string) {
  return useQuery({
    queryKey: ["investigations", workspaceId],
    queryFn: () =>
      api.get<ApiResponse<Investigation[]>>(`/workspaces/${workspaceId}/investigations/`),
    enabled: !!workspaceId,
  });
}

export function useCreateInvestigation(workspaceId: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      question: string;
      insight_id?: string;
      scope?: "documents" | "web" | "both";
    }) =>
      api.post<ApiResponse<Investigation>>(
        `/workspaces/${workspaceId}/investigations/`,
        body,
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["investigations", workspaceId] });
      void qc.invalidateQueries({ queryKey: ["insights", workspaceId] });
    },
  });
}
