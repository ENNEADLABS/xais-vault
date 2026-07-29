"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ApiResponse } from "@/lib/api";
import type { Source } from "@/types/api";

export function useSources(workspaceId: string) {
  return useQuery({
    queryKey: ["sources", workspaceId],
    queryFn: () => api.get<ApiResponse<Source[]>>(`/workspaces/${workspaceId}/sources/`),
    enabled: !!workspaceId,
  });
}

export function useUploadSource(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.upload<ApiResponse<Source>>(
        `/workspaces/${workspaceId}/sources/`,
        formData,
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sources", workspaceId] });
    },
  });
}
