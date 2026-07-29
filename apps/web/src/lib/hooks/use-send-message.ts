"use client";

import { useRef, useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { API_URL } from "@/lib/api";
import { useUIStore } from "@/stores/ui-store";
import type { Citation } from "@/types/api";

export interface RagContext {
  chunkCount: number;
  sourceCount: number;
  avgSimilarity: number;
  tokensUsed: number;
  tokensBudget: number;
  sourcesUsed: Array<{ id: string; name: string; chunk_count: number }>;
}

async function getToken(): Promise<string | undefined> {
  const { createClient } = await import("@/lib/supabase/client");
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token;
}

async function parseSSE(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  handlers: {
    onSession: (id: string) => void;
    onContext: (ctx: RagContext) => void;
    onContent: (text: string) => void;
    onCitations: (c: Citation[]) => void;
    onError: (msg: string) => void;
    onDone: () => void;
  },
) {
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ") && currentEvent) {
        try {
          const data = JSON.parse(line.slice(6)) as Record<string, unknown>;
          if (currentEvent === "session") handlers.onSession(data.id as string);
          else if (currentEvent === "context")
            handlers.onContext({
              chunkCount: data.chunk_count as number,
              sourceCount: data.source_count as number,
              avgSimilarity: data.avg_similarity as number,
              tokensUsed: data.tokens_used as number,
              tokensBudget: data.tokens_budget as number,
              sourcesUsed: data.sources_used as RagContext["sourcesUsed"],
            });
          else if (currentEvent === "content")
            handlers.onContent(data.text as string);
          else if (currentEvent === "citations")
            handlers.onCitations(data.citations as Citation[]);
          else if (currentEvent === "error")
            handlers.onError(data.message as string);
          else if (currentEvent === "done") handlers.onDone();
        } catch {
          // malformed JSON — ignore
        }
        currentEvent = "";
      }
    }
  }
}

interface SendOptions {
  content: string;
  sessionId: string | null;
  onSessionCreated: (id: string) => void;
  sourceIds?: string[];
}

export function useSendMessage(workspaceId: string) {
  const queryClient = useQueryClient();
  const organizationId = useUIStore((s) => s.organizationId);
  const abortRef = useRef<AbortController | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [streamingRagContext, setStreamingRagContext] = useState<RagContext | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async ({ content, sessionId, onSessionCreated, sourceIds }: SendOptions) => {
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsStreaming(true);
      setStreamingText("");
      setStreamingCitations([]);
      setStreamingRagContext(null);
      setStreamError(null);

      let resolvedSessionId = sessionId;

      try {
        const token = await getToken();
        const res = await fetch(`${API_URL}/api/v2/workspaces/${workspaceId}/chat/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(organizationId ? { "X-Organization-ID": organizationId } : {}),
          },
          body: JSON.stringify({
            content,
            session_id: sessionId,
            stream: true,
            ...(sourceIds && sourceIds.length > 0 ? { source_ids: sourceIds } : {}),
          }),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          throw new Error("Stream unavailable");
        }

        const reader = res.body.getReader();
        await parseSSE(reader, {
          onSession: (id) => {
            resolvedSessionId = id;
            onSessionCreated(id);
            void queryClient.invalidateQueries({
              queryKey: ["chat-sessions", workspaceId],
            });
          },
          onContext: (ctx) => setStreamingRagContext(ctx),
          onContent: (text) => setStreamingText((prev) => prev + text),
          onCitations: (c) => setStreamingCitations(c),
          onError: (msg) => setStreamError(msg),
          onDone: () => {},
        });

        // Wait for messages refetch BEFORE clearing streaming state —
        // otherwise the streaming bubble vanishes while messages are still stale.
        await queryClient.invalidateQueries({
          queryKey: ["chat-messages", resolvedSessionId],
        });
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setStreamError("Erreur de connexion");
        }
      } finally {
        setIsStreaming(false);
        setStreamingText("");
        setStreamingCitations([]);
        setStreamingRagContext(null);
      }
    },
    [workspaceId, organizationId, queryClient],
  );

  return {
    sendMessage,
    isStreaming,
    streamingText,
    streamingCitations,
    streamingRagContext,
    streamError,
  };
}
