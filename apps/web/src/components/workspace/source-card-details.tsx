"use client";

import { useTranslations } from "next-intl";
import { MessageSquare, FileSearch } from "lucide-react";
import { useWorkspaceInteractionStore } from "@/stores/workspace-interaction-store";
import type { Source } from "@/types/api";

interface SourceCardDetailsProps {
  source: Source;
}

export function SourceCardDetails({ source }: SourceCardDetailsProps) {
  const t = useTranslations("workspace_page");
  const setPrefill = useWorkspaceInteractionStore((s) => s.setPrefillChatMessage);

  return (
    <div className="space-y-3 px-2.5 pb-3">
      {/* Résumé */}
      {source.summary && (
        <div>
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-vault-text-muted">
            {t("sourceSummary")}
          </p>
          <p className="text-[13px] leading-relaxed text-vault-text-secondary">
            {source.summary}
          </p>
        </div>
      )}

      {/* Topics */}
      {source.topics && source.topics.length > 0 && (
        <div>
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-vault-text-muted">
            {t("sourceTopics")}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {source.topics.map((topic) => (
              <button
                key={topic}
                type="button"
                onClick={() =>
                  setPrefill(t("topicPrompt", { topic, source: source.name }))
                }
                className="rounded-full bg-vault-accent/10 px-2.5 py-0.5 text-xs font-medium text-vault-accent transition-colors hover:bg-vault-accent/20"
              >
                {topic}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Stats */}
      {(source.page_count != null || source.word_count != null) && (
        <div className="flex items-center gap-3 text-xs text-vault-text-muted">
          {source.page_count != null && (
            <span>{t("sourcePages", { count: source.page_count })}</span>
          )}
          {source.word_count != null && (
            <span>
              {t("sourceWords", { count: source.word_count.toLocaleString() })}
            </span>
          )}
        </div>
      )}

      {/* Questions suggérées */}
      {source.suggested_questions && source.suggested_questions.length > 0 && (
        <div>
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-vault-text-muted">
            {t("sourceSuggestedQuestions")}
          </p>
          <div className="space-y-1">
            {source.suggested_questions.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => setPrefill(q)}
                className="block w-full rounded-md px-2 py-1.5 text-left text-[13px] text-vault-text-secondary transition-colors hover:bg-vault-surface-active"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={() =>
            setPrefill(t("askSourcePrompt", { source: source.name }))
          }
          className="inline-flex items-center gap-1.5 rounded-md bg-vault-accent/10 px-2.5 py-1.5 text-xs font-medium text-vault-accent transition-colors hover:bg-vault-accent/20"
        >
          <MessageSquare className="h-3.5 w-3.5" />
          {t("askQuestion")}
        </button>
        <button
          type="button"
          onClick={() =>
            setPrefill(t("scanSourcePrompt", { source: source.name }))
          }
          className="inline-flex items-center gap-1.5 rounded-md bg-vault-surface-active px-2.5 py-1.5 text-xs font-medium text-vault-text-secondary transition-colors hover:bg-vault-border"
        >
          <FileSearch className="h-3.5 w-3.5" />
          {t("scanSource")}
        </button>
      </div>
    </div>
  );
}
