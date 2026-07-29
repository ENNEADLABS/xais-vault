"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ApiResponse, type PaginatedResponse } from "@/lib/api";
import type { Webhook, WebhookCreated, WebhookDelivery } from "@/types/api";

export function useWebhooks(page = 1) {
  return useQuery({
    queryKey: ["webhooks", page],
    queryFn: () =>
      api.get<PaginatedResponse<Webhook>>(`/webhooks/?page=${page}`),
  });
}

export function useCreateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      url: string;
      events: string[];
      is_active?: boolean;
    }) => api.post<ApiResponse<WebhookCreated>>("/webhooks/", data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });
}

export function useUpdateWebhook(webhookId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      url?: string;
      events?: string[];
      is_active?: boolean;
    }) => api.patch<ApiResponse<Webhook>>(`/webhooks/${webhookId}`, data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });
}

export function useDeleteWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (webhookId: string) => api.delete(`/webhooks/${webhookId}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });
}

export function useRotateWebhookSecret() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (webhookId: string) =>
      api.post<ApiResponse<WebhookCreated>>(
        `/webhooks/${webhookId}/rotate-secret`,
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });
}

export function useTestWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (webhookId: string) =>
      api.post<ApiResponse<{ job_id: string; status: string }>>(
        `/webhooks/${webhookId}/test`,
      ),
    onSuccess: (_data, webhookId) => {
      void qc.invalidateQueries({
        queryKey: ["webhook-deliveries", webhookId],
      });
    },
  });
}

export function useWebhookDeliveries(webhookId: string, page = 1) {
  return useQuery({
    queryKey: ["webhook-deliveries", webhookId, page],
    queryFn: () =>
      api.get<PaginatedResponse<WebhookDelivery>>(
        `/webhooks/${webhookId}/deliveries?page=${page}`,
      ),
    enabled: !!webhookId,
  });
}
