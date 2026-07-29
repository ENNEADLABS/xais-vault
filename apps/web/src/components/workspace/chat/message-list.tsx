"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { MessageSquare, Upload, AlertTriangle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageBubble } from "./message-bubble";
import type { ChatMessage, Citation } from "@/types/api";
import type { RagContext } from "@/lib/hooks/use-send-message";
import type { WorkspaceContext } from "../smart-prompts-bar";

type FeedbackValue = "positive" | "negative" | null;

interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
  isStreaming: boolean;
  streamingText: string;
  streamingCitations: Citation[];
  streamingRagContext?: RagContext | null;
  onSaveAsNote?: (messageId: string, content: string) => void;
  onSuggestionClick?: (text: string) => void;
  onFeedback?: (messageId: string, feedback: FeedbackValue) => void;
  dealContext?: WorkspaceContext;
  totalPages?: number;
  error?: string | null;
}

export function MessageList({
  messages,
  isLoading,
  isStreaming,
  streamingText,
  streamingCitations,
  streamingRagContext,
  onSaveAsNote,
  onSuggestionClick,
  onFeedback,
  dealContext,
  totalPages = 0,
  error,
}: MessageListProps) {
  const t = useTranslations("chat");
  const sentinelRef = useRef<HTMLDivElement>(null);
  const isNearBottom = useRef(true);

  function handleScroll(e: React.UIEvent<HTMLDivElement>) {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    isNearBottom.current = scrollHeight - scrollTop - clientHeight < 100;
  }

  useEffect(() => {
    if (isNearBottom.current) {
      sentinelRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length, streamingText]);

  if (isLoading) {
    return (
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4" role="status" aria-busy="true" aria-label={t("loading")}>
        <Skeleton className="h-12 w-3/4 self-end rounded-2xl" />
        <Skeleton className="h-20 w-4/5 rounded-2xl" />
        <Skeleton className="h-10 w-2/3 self-end rounded-2xl" />
      </div>
    );
  }

  if (messages.length === 0 && !isStreaming) {
    const hasReadySources = dealContext && dealContext.readyCount > 0;
    const hasSources = dealContext && dealContext.sourceCount > 0;

    // Suggestions contextuelles basées sur l'état
    const suggestions = hasReadySources
      ? [
          t("suggestions.redFlags"),
          t("suggestions.financials"),
          t("suggestions.risks"),
        ]
      : [];

    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
        <div className="rounded-2xl bg-linear-to-br from-vault-accent/5 to-transparent p-6">
          {hasSources ? (
            <MessageSquare className="h-10 w-10 text-vault-accent/40" />
          ) : (
            <Upload className="h-10 w-10 text-vault-text-muted/40" />
          )}
        </div>
        <div className="text-center space-y-1">
          {hasReadySources ? (
            <>
              <p className="text-sm font-medium">{t("emptyStateReady")}</p>
              <p className="text-[12px] text-vault-text-muted">
                {t("emptyStateContext", {
                  sources: dealContext.readyCount,
                  pages: totalPages,
                })}
              </p>
              <p className="text-[12px] text-vault-text-muted mt-2">
                {t("emptyStateHint")}
              </p>
            </>
          ) : (
            <p className="text-sm text-vault-text-muted">
              {t("emptyStateNoSources")}
            </p>
          )}
        </div>
        {onSuggestionClick && suggestions.length > 0 && (
          <div className="flex flex-wrap justify-center gap-2 mt-2 max-w-sm">
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSuggestionClick(s)}
                className="border border-vault-border rounded-lg px-3 py-2 text-[12px] text-vault-text-secondary hover:bg-vault-surface-hover hover:text-vault-text transition-colors duration-150 cursor-pointer"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className="flex flex-1 flex-col overflow-y-auto px-4 py-4"
      onScroll={handleScroll}
      role="log"
      aria-live="polite"
      aria-label={t("messageList")}
    >
      <div className="mx-auto w-full max-w-2xl space-y-4">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            role={msg.role}
            content={msg.content}
            citations={msg.citations}
            messageId={msg.id}
            onSaveAsNote={onSaveAsNote}
            onFeedback={onFeedback}
          />
        ))}

        {isStreaming && (
          <MessageBubble
            role="assistant"
            content={streamingText.replace(/\[SOURCE:[^\]]*\]/g, "")}
            citations={
              streamingCitations && streamingCitations.length > 0
                ? streamingCitations
                : null
            }
            ragContext={streamingRagContext}
            isStreaming
          />
        )}

        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-400">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div ref={sentinelRef} />
      </div>
    </div>
  );
}
