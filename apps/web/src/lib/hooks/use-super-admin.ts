"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  PlatformOverview,
  OrgMetrics,
  SummarizationStats,
  SuperAdminUserActivity,
  SuperAdminActivityItem,
  SuperAdminErrorItem,
} from "@/types/api";

export function useSuperAdminCheck() {
  return useQuery({
    queryKey: ["super-admin", "check"],
    queryFn: () => api.get<{ is_super_admin: boolean }>("/super-admin/check"),
    staleTime: Infinity,
  });
}

export function useSummarizationStats() {
  return useQuery({
    queryKey: ["super-admin", "summarization"],
    queryFn: () => api.get<SummarizationStats>("/super-admin/summarization"),
    staleTime: 60_000,
  });
}

export function usePlatformOverview() {
  return useQuery({
    queryKey: ["super-admin", "overview"],
    queryFn: () => api.get<PlatformOverview>("/super-admin/overview"),
    staleTime: 60_000,
  });
}

export function useOrgMetrics() {
  return useQuery({
    queryKey: ["super-admin", "organizations"],
    queryFn: () => api.get<OrgMetrics[]>("/super-admin/organizations"),
    staleTime: 60_000,
  });
}

export function useUserActivity(orgId?: string | null) {
  const params = new URLSearchParams();
  if (orgId) params.set("org_id", orgId);
  const qs = params.toString();

  return useQuery({
    queryKey: ["super-admin", "users", orgId],
    queryFn: () =>
      api.get<SuperAdminUserActivity[]>(`/super-admin/users${qs ? `?${qs}` : ""}`),
    staleTime: 60_000,
  });
}

export function useGlobalActivity(limit = 100) {
  return useQuery({
    queryKey: ["super-admin", "activity", limit],
    queryFn: () =>
      api.get<SuperAdminActivityItem[]>(`/super-admin/activity?limit=${limit}`),
    refetchInterval: 30_000,
  });
}

export function useErrorLog(limit = 50) {
  return useQuery({
    queryKey: ["super-admin", "errors", limit],
    queryFn: () =>
      api.get<SuperAdminErrorItem[]>(`/super-admin/errors?limit=${limit}`),
    refetchInterval: 30_000,
  });
}
