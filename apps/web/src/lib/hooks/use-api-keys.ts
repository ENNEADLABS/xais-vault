"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ApiResponse, type PaginatedResponse } from "@/lib/api";
import type { ApiKey, ApiKeyCreated, ApiKeyWithUsage } from "@/types/api";

export function useApiKeys(page = 1) {
  return useQuery({
    queryKey: ["api-keys", page],
    queryFn: () => api.get<PaginatedResponse<ApiKey>>(`/api-keys/?page=${page}`),
  });
}

export function useApiKey(keyId: string) {
  return useQuery({
    queryKey: ["api-key", keyId],
    queryFn: () => api.get<ApiResponse<ApiKeyWithUsage>>(`/api-keys/${keyId}`),
    enabled: !!keyId,
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      name: string;
      scopes?: string[];
      rpm_limit?: number;
      rpd_limit?: number;
    }) => api.post<ApiResponse<ApiKeyCreated>>("/api-keys/", data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
}

export function useUpdateApiKey(keyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      name?: string;
      scopes?: string[];
      rpm_limit?: number;
      rpd_limit?: number;
      is_active?: boolean;
    }) => api.patch<ApiResponse<ApiKey>>(`/api-keys/${keyId}`, data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
      void qc.invalidateQueries({ queryKey: ["api-key", keyId] });
    },
  });
}

export function useRevokeApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => api.delete(`/api-keys/${keyId}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
}

export function useRotateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) =>
      api.post<ApiResponse<ApiKeyCreated>>(`/api-keys/${keyId}/rotate`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
}
