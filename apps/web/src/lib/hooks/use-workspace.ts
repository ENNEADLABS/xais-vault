"use client";

import { useQuery } from "@tanstack/react-query";
import { api, type ApiResponse } from "@/lib/api";
import type { Workspace } from "@/types/api";

export function useWorkspace(workspaceId: string) {
  return useQuery({
    queryKey: ["workspace", workspaceId],
    queryFn: () => api.get<ApiResponse<Workspace>>(`/workspaces/${workspaceId}`),
    enabled: !!workspaceId,
  });
}
