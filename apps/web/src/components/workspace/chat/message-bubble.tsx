"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTranslations } from "next-intl";
import { StickyNote, ThumbsUp, ThumbsDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { CitationBadge } from "./citation-badge";
import { RagContextIndicator } from "./rag-context-indicator";
import type { Citation } from "@/types/api";
import type { RagContext } from "@/lib/hooks/use-send-message";

type FeedbackValue = "positive" | "negative" | null;

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[] | null;
  ragContext?: RagContext | null;
  isStreaming?: boolean;
  messageId?: string;
  onSaveAsNote?: (messageId: string, content: string) => void;
  onFeedback?: (messageId: string, feedback: FeedbackValue) => void;
}

export function MessageBubble({
  role,
  content,
  citations,
  ragContext,
  isStreaming,
  messageId,
  onSaveAsNote,
  onFeedback,
}: MessageBubbleProps) {
  const t = useTranslations("chat");
  const isUser = role === "user";
  const [feedback, setFeedback] = useState<FeedbackValue>(null);

  function handleFeedback(value: FeedbackValue) {
    const next = feedback === value ? null : value;
    setFeedback(next);
    if (messageId && onFeedback) {
      onFeedback(messageId, next);
    }
  }

  return (
    <div
      className={cn(
        "group flex flex-col gap-0.5",
        isUser ? "items-end" : "items-start",
      )}
    >
      <span className="px-1 text-[12px] font-medium uppercase tracking-wider text-vault-text-muted">
        {isUser ? "Vous" : "XAIS"}
      </span>
      <div
        className={cn(
          "max-w-[85%] px-4 py-3 text-[14px] leading-relaxed font-reading",
          isUser
            ? "rounded-[16px_16px_4px_16px] bg-vault-user-bubble text-vault-text"
            : "vault-card rounded-[16px_16px_16px_4px] bg-vault-surface border border-vault-border text-vault-text",
        )}
      >
        {isStreaming && !content ? (
          <span className="flex items-center gap-1 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-vault-accent animate-bounce" />
            <span className="h-1.5 w-1.5 rounded-full bg-vault-accent animate-bounce [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 rounded-full bg-vault-accent animate-bounce [animation-delay:300ms]" />
          </span>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              ul: ({ children }) => (
                <ul className="mb-2 list-disc pl-4">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="mb-2 list-decimal pl-4">{children}</ol>
              ),
              code: ({ children }) => (
                <code className="rounded bg-vault-bg/80 px-1.5 py-0.5 font-mono text-xs text-vault-accent">
                  {children}
                </code>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
        )}
      </div>

      {!isUser && ragContext && (
        <RagContextIndicator context={ragContext} />
      )}

      {!isUser && citations && citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-1">
          {citations.map((c, i) => (
            <CitationBadge
              key={`${c.source_id}-${c.page_number}-${c.quote?.slice(0, 30) ?? i}`}
              citation={c}
            />
          ))}
        </div>
      )}

      {!isUser && !isStreaming && messageId && (
        <div className="opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity flex items-center gap-1 ml-1">
          <button
            type="button"
            onClick={() => handleFeedback("positive")}
            className={cn(
              "p-0.5 rounded transition-colors",
              feedback === "positive"
                ? "text-green-500"
                : "text-vault-text-muted hover:text-green-500",
            )}
            aria-label={t("feedbackPositive")}
          >
            <ThumbsUp className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => handleFeedback("negative")}
            className={cn(
              "p-0.5 rounded transition-colors",
              feedback === "negative"
                ? "text-red-500"
                : "text-vault-text-muted hover:text-red-500",
            )}
            aria-label={t("feedbackNegative")}
          >
            <ThumbsDown className="h-3.5 w-3.5" />
          </button>
          {onSaveAsNote && (
            <button
              type="button"
              onClick={() => onSaveAsNote(messageId, content)}
              className="flex items-center gap-1 px-1.5 py-0.5 rounded text-vault-text-muted hover:text-purple-400 hover:bg-purple-500/10 transition-colors"
              aria-label={t("saveAsNote")}
            >
              <StickyNote className="h-3.5 w-3.5" />
              <span className="text-[11px]">{t("saveAsNote")}</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
