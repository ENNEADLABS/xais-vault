"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiResponse } from "@/lib/api";
import type { BillingStatus } from "@/types/api";

export function useBillingStatus() {
  return useQuery({
    queryKey: ["billing-status"],
    queryFn: () => api.get<ApiResponse<BillingStatus>>("/billing/status"),
    staleTime: 5 * 60 * 1000, // 5 minutes — évite les requêtes fréquentes
  });
}

export function useCreateCheckout() {
  return useMutation({
    mutationFn: (data: {
      price_id: string;
      success_url: string;
      cancel_url: string;
    }) =>
      api.post<ApiResponse<{ url: string }>>("/billing/checkout", data).then(
        (res) => res.data?.url ?? ""
      ),
    onSuccess: (url) => {
      window.location.href = url;
    },
  });
}

export function useCreatePortal() {
  return useMutation({
    mutationFn: (return_url: string) =>
      api
        .post<ApiResponse<{ url: string }>>("/billing/portal", { return_url })
        .then((res) => res.data?.url ?? ""),
    onSuccess: (url) => {
      window.location.href = url;
    },
  });
}
