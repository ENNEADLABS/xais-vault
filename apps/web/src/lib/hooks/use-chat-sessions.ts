"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ApiResponse } from "@/lib/api";
import type { ChatSession } from "@/types/api";

export function useChatSessions(workspaceId: string) {
  return useQuery({
    queryKey: ["chat-sessions", workspaceId],
    queryFn: () =>
      api.get<ApiResponse<ChatSession[]>>(`/workspaces/${workspaceId}/chat/sessions`),
    enabled: !!workspaceId,
  });
}

export function useRenameSession(workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, title }: { sessionId: string; title: string }) =>
      api.patch<ApiResponse<ChatSession>>(
        `/workspaces/${workspaceId}/chat/sessions/${sessionId}`,
        { title },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["chat-sessions", workspaceId],
      });
    },
  });
}

export function useDeleteSession(workspaceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      api.delete(`/workspaces/${workspaceId}/chat/sessions/${sessionId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["chat-sessions", workspaceId],
      });
    },
  });
}
