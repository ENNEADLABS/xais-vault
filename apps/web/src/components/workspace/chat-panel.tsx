"use client";

import { useState, useMemo, useCallback } from "react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { useChatSessions } from "@/lib/hooks/use-chat-sessions";
import { useChatMessages } from "@/lib/hooks/use-chat-messages";
import { useSendMessage } from "@/lib/hooks/use-send-message";
import { useCreateNote } from "@/lib/hooks/use-notes";
import { useCreateDeliverable } from "@/lib/hooks/use-deliverables";
import { useSources } from "@/lib/hooks/use-sources";
import { useWorkspace } from "@/lib/hooks/use-workspace";
import { useInsights } from "@/lib/hooks/use-insights";
import { useInvestigations } from "@/lib/hooks/use-investigations";
import { useWorkspaceInteractionStore } from "@/stores/workspace-interaction-store";
import { api } from "@/lib/api";
import { SessionSelector } from "./chat/session-selector";
import { FocusSourceIndicator } from "./chat/focus-source-indicator";
import { MessageList } from "./chat/message-list";
import { ChatInput } from "./chat/chat-input";
import { SmartPromptsBar, type WorkspaceContext } from "./smart-prompts-bar";

interface ChatPanelProps {
  workspaceId: string;
}

export function ChatPanel({ workspaceId }: ChatPanelProps) {
  const t = useTranslations("chat");
  const tNotes = useTranslations("notes");
  // undefined = pas encore choisi → auto-select première session
  // null = user a choisi "nouvelle session"
  const [activeSessionId, setActiveSessionId] = useState<
    string | null | undefined
  >(undefined);

  const { data: sessionsData } = useChatSessions(workspaceId);
  const sessions = useMemo(() => sessionsData?.data ?? [], [sessionsData]);

  const resolvedSessionId =
    activeSessionId === undefined ? (sessions[0]?.id ?? null) : activeSessionId;

  const { data: messagesData, isLoading: isLoadingMessages, error: messagesError } = useChatMessages(
    workspaceId,
    resolvedSessionId,
  );
  const {
    sendMessage,
    isStreaming,
    streamingText,
    streamingCitations,
    streamingRagContext,
    streamError,
  } = useSendMessage(workspaceId);
  const createNote = useCreateNote(workspaceId);
  const createDeliverable = useCreateDeliverable(workspaceId);

  // Données contextuelles pour smart prompts
  const { data: workspaceData } = useWorkspace(workspaceId);
  const { data: sourcesData } = useSources(workspaceId);
  const { data: findingsData } = useInsights(workspaceId);
  const { data: investigationsData } = useInvestigations(workspaceId);

  const sources = useMemo(() => sourcesData?.data ?? [], [sourcesData]);
  const ragFilterSourceIds = useWorkspaceInteractionStore((s) => s.ragFilterSourceIds);

  const messages = messagesData?.data?.messages ?? [];

  // Contexte du workspace pour les smart prompts et l'empty state
  const workspaceContext = useMemo<WorkspaceContext>(() => {
    const allSources = sources;
    const insights = findingsData?.data ?? [];
    const investigations = investigationsData?.data ?? [];

    return {
      sourceCount: allSources.length,
      processingCount: allSources.filter((s) => s.status === "processing").length,
      readyCount: allSources.filter((s) => s.status === "ready").length,
      scanStatus: workspaceData?.data?.scan_status ?? "pending",
      insightsCount: insights.length,
      criticalCount: insights.filter((f) => f.severity === "critical").length,
      investigationCount: investigations.filter(
        (i) => i.status === "completed",
      ).length,
    };
  }, [sources, findingsData, investigationsData, workspaceData]);

  // Total pages pour l'indicateur de contexte
  const totalPages = useMemo(
    () =>
      sources
        .filter((s) => s.status === "ready")
        .reduce((sum, s) => sum + (s.page_count ?? 0), 0),
    [sources],
  );

  const contextLabel = useMemo(() => {
    if (workspaceContext.readyCount === 0) return null;
    return t("contextIndicator", {
      sources: workspaceContext.readyCount,
      pages: totalPages,
    });
  }, [workspaceContext.readyCount, totalPages, t]);

  const handleSaveAsNote = useCallback(
    (messageId: string, content: string) => {
      createNote.mutate(
        { content, linked_message_id: messageId },
        { onSuccess: () => toast.success(tNotes("noteSaved")) },
      );
    },
    [createNote, tNotes],
  );

  // Feedback sur les messages assistant
  const handleFeedback = useCallback(
    (messageId: string, feedback: "positive" | "negative" | null) => {
      void api
        .patch(`/chat/messages/${messageId}/feedback`, { feedback })
        .then(() => toast.success(t("feedbackSaved")))
        .catch(() => {
          // Silently fail — le feedback n'est pas critique
        });
    },
    [t],
  );

  function handleSend(content: string) {
    void sendMessage({
      content,
      sessionId: resolvedSessionId,
      onSessionCreated: (id) => setActiveSessionId(id),
      sourceIds: ragFilterSourceIds.length > 0 ? ragFilterSourceIds : undefined,
    });
  }

  // Smart prompts callback
  function handleSmartPrompt(prompt: string) {
    if (!prompt || isStreaming) return;
    handleSend(prompt);
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <SessionSelector
        workspaceId={workspaceId}
        sessions={sessions}
        activeSessionId={resolvedSessionId}
        onSelect={setActiveSessionId}
      />
      <FocusSourceIndicator />
      <SmartPromptsBar
        context={workspaceContext}
        onPrompt={handleSmartPrompt}
        disabled={isStreaming || createDeliverable.isPending}
      />
      <MessageList
        messages={messages}
        isLoading={isLoadingMessages}
        isStreaming={isStreaming}
        streamingText={streamingText}
        streamingCitations={streamingCitations}
        streamingRagContext={streamingRagContext}
        onSaveAsNote={handleSaveAsNote}
        onSuggestionClick={handleSend}
        onFeedback={handleFeedback}
        dealContext={workspaceContext}
        totalPages={totalPages}
        error={streamError ?? (messagesError ? String(messagesError) : null)}
      />
      <ChatInput
        onSend={handleSend}
        isStreaming={isStreaming}
        sources={sources}
        contextLabel={contextLabel}
      />
    </div>
  );
}
