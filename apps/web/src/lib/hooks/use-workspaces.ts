"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type PaginatedResponse, type ApiResponse } from "@/lib/api";
import type { Workspace } from "@/types/api";

interface WorkspacesFilters {
  status?: "active" | "archived" | "closed" | null;
  page?: number;
}

export interface WorkspaceCreateInput {
  name: string;
  emoji: string;
  description?: string;
  deal_type?: string;
  sector?: string;
  target_company?: string;
}

export function useWorkspaces(filters: WorkspacesFilters = {}) {
  const { status, page = 1 } = filters;

  const params = new URLSearchParams();
  if (status) params.set("status", status);
  params.set("page", String(page));

  const queryString = params.toString();
  const path = `/workspaces/${queryString ? `?${queryString}` : ""}`;

  return useQuery({
    queryKey: ["workspaces", { status, page }],
    queryFn: () => api.get<PaginatedResponse<Workspace>>(path),
  });
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: WorkspaceCreateInput) =>
      api.post<ApiResponse<Workspace>>("/workspaces/", input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });
}

export function useUpdateWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ workspaceId, ...update }: { workspaceId: string; name?: string; status?: string }) =>
      api.patch<ApiResponse<Workspace>>(`/workspaces/${workspaceId}`, update),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });
}

export function useDeleteWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (workspaceId: string) => api.delete(`/workspaces/${workspaceId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });
}
