"use client";

import { useQuery } from "@tanstack/react-query";
import { api, type ApiResponse } from "@/lib/api";
import type {
  ActivityLogResponse,
  ApiKeysUsageResponse,
  OrgOverviewResponse,
  UsageStatsResponse,
} from "@/types/api";

export function useAdminUsage(months = 6) {
  return useQuery({
    queryKey: ["admin", "usage", months],
    queryFn: () =>
      api.get<ApiResponse<UsageStatsResponse>>(`/admin/usage?months=${months}`),
    staleTime: 2 * 60 * 1000,
  });
}

export function useAdminOverview() {
  return useQuery({
    queryKey: ["admin", "overview"],
    queryFn: () =>
      api.get<ApiResponse<OrgOverviewResponse>>("/admin/overview"),
    staleTime: 2 * 60 * 1000,
  });
}

export function useAdminApiKeysUsage() {
  return useQuery({
    queryKey: ["admin", "api-keys-usage"],
    queryFn: () =>
      api.get<ApiResponse<ApiKeysUsageResponse>>("/admin/api-keys/usage"),
    staleTime: 5 * 60 * 1000,
  });
}

export function useAdminActivity(limit = 50) {
  return useQuery({
    queryKey: ["admin", "activity", limit],
    queryFn: () =>
      api.get<ApiResponse<ActivityLogResponse>>(
        `/admin/activity?limit=${limit}`,
      ),
    staleTime: 60 * 1000,
  });
}
