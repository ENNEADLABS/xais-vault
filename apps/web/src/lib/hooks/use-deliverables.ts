"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ApiResponse } from "@/lib/api";
import type { Deliverable } from "@/types/api";

export function useDeliverables(workspaceId: string) {
  return useQuery({
    queryKey: ["deliverables", workspaceId],
    queryFn: () =>
      api.get<ApiResponse<Deliverable[]>>(`/workspaces/${workspaceId}/deliverables/`),
    enabled: !!workspaceId,
  });
}

interface CreateDeliverableInput {
  type: Deliverable["type"];
  name: string;
  options?: Record<string, unknown>;
}

export function useCreateDeliverable(workspaceId: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (input: CreateDeliverableInput) =>
      api.post<ApiResponse<Deliverable>>(
        `/workspaces/${workspaceId}/deliverables/`,
        input,
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["deliverables", workspaceId] });
    },
  });
}
