"use client";

import { useRef, useState, useEffect, type KeyboardEvent } from "react";
import { useTranslations } from "next-intl";
import { SendHorizontal, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { useMediaQuery, BREAKPOINTS } from "@/hooks/use-media-query";
import { useMentionDropdown } from "@/hooks/use-mention-dropdown";
import { useWorkspaceInteractionStore } from "@/stores/workspace-interaction-store";
import type { Source } from "@/types/api";

interface ChatInputProps {
  onSend: (content: string) => void;
  isStreaming: boolean;
  sources?: Source[];
  contextLabel?: string | null;
}

export function ChatInput({
  onSend,
  isStreaming,
  sources = [],
  contextLabel,
}: ChatInputProps) {
  const t = useTranslations("chat");
  const isDesktop = useMediaQuery(BREAKPOINTS.md);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [value, setValue] = useState(
    () => useWorkspaceInteractionStore.getState().prefillChatMessage ?? "",
  );

  // Prefill depuis le store (clic topic/question dans sources)
  const setFocusSource = useWorkspaceInteractionStore((s) => s.setFocusSource);

  const {
    showMention,
    mentionIndex,
    filteredSources,
    handleMentionDetection,
    selectMention,
    handleMentionKeyDown,
    setMentionIndex,
  } = useMentionDropdown({ sources });

  useEffect(() => {
    const initialPrefill = useWorkspaceInteractionStore.getState().prefillChatMessage;
    if (initialPrefill) {
      useWorkspaceInteractionStore.getState().setPrefillChatMessage(null);
      textareaRef.current?.focus();
    }

    return useWorkspaceInteractionStore.subscribe((state, previousState) => {
      const nextPrefill = state.prefillChatMessage;
      if (!nextPrefill || nextPrefill === previousState.prefillChatMessage) return;

      setValue(nextPrefill);
      state.setPrefillChatMessage(null);
      textareaRef.current?.focus();
    });
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 150)}px`;
  }, [value]);

  function handleChange(newValue: string) {
    setValue(newValue);
    handleMentionDetection(newValue);
  }

  function doSelectMention(source: Source) {
    const newValue = selectMention(source, value);
    setValue(newValue);
    setFocusSource(source.id, source.name);
    textareaRef.current?.focus();
  }

  function handleSend() {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setValue("");
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    const consumed = handleMentionKeyDown(e.key, e.shiftKey, e.metaKey, e.ctrlKey);
    if (consumed) {
      e.preventDefault();
      // Enter dans le dropdown → sélectionner
      if (e.key === "Enter") {
        const selected = filteredSources[mentionIndex];
        if (selected) doSelectMention(selected);
      }
      return;
    }

    if (e.key === "Enter") {
      if (isDesktop) {
        if (e.metaKey || e.ctrlKey) {
          e.preventDefault();
          handleSend();
        }
      } else {
        if (!e.shiftKey) {
          e.preventDefault();
          handleSend();
        }
      }
    }
  }

  return (
    <div className="p-4">
      <div className="relative">
        {/* Dropdown de mention @source */}
        {showMention && filteredSources.length > 0 && (
          <div
            ref={dropdownRef}
            className="absolute bottom-full left-0 right-0 mb-1 max-h-48 overflow-y-auto rounded-lg border border-vault-border bg-vault-surface shadow-lg z-10"
          >
            {filteredSources.map((source, i) => (
              <button
                key={source.id}
                type="button"
                className={cn(
                  "flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] transition-colors",
                  i === mentionIndex
                    ? "bg-vault-accent/10 text-vault-accent"
                    : "text-vault-text hover:bg-vault-surface-hover",
                )}
                onMouseDown={(e) => {
                  e.preventDefault();
                  doSelectMention(source);
                }}
                onMouseEnter={() => setMentionIndex(i)}
              >
                <FileText className="h-3.5 w-3.5 shrink-0 text-vault-text-muted" />
                <span className="flex-1 truncate">{source.name}</span>
                {source.page_count && (
                  <span className="text-[11px] text-vault-text-muted">
                    {source.page_count}p
                  </span>
                )}
              </button>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2 p-3 bg-vault-surface border border-vault-border rounded-[14px] focus-within:border-vault-accent transition-colors">
          <textarea
            ref={textareaRef}
            className="flex-1 resize-none bg-transparent text-[14px] text-vault-text placeholder:text-vault-text-muted outline-none min-h-6 max-h-30 disabled:opacity-50"
            placeholder={t("inputPlaceholder")}
            value={value}
            onChange={(e) => handleChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            rows={1}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!value.trim() || isStreaming}
            className={cn(
              "h-8.5 w-8.5 flex items-center justify-center rounded-full transition-colors shrink-0",
              value.trim()
                ? "bg-vault-accent text-vault-bg hover:bg-vault-accent-hover"
                : "bg-vault-border text-vault-text-muted",
            )}
          >
            <SendHorizontal className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="hidden md:flex items-center justify-between px-1 pt-1">
        <span className="text-[11px] text-vault-text-muted">
          <kbd className="rounded border border-vault-border px-1 py-0.5 text-[10px]">
            &#8984;
          </kbd>
          {" + "}
          <kbd className="rounded border border-vault-border px-1 py-0.5 text-[10px]">
            Enter
          </kbd>
          {` ${t("sendHint")}`}
        </span>
        {contextLabel && (
          <span className="text-[11px] text-vault-text-muted">
            {contextLabel}
          </span>
        )}
      </div>
    </div>
  );
}
