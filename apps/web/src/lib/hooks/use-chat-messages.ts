"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ChatSession, ChatMessage } from "@/types/api";

interface SessionWithMessages {
  session: ChatSession;
  messages: ChatMessage[];
}

export function useChatMessages(workspaceId: string, sessionId: string | null) {
  return useQuery({
    queryKey: ["chat-messages", sessionId],
    queryFn: () =>
      api.get<{ data: SessionWithMessages }>(
        `/workspaces/${workspaceId}/chat/sessions/${sessionId}`,
      ),
    enabled: !!sessionId,
  });
}
