"use client";

import { useTranslations } from "next-intl";
import { Sparkles } from "lucide-react";
import { useSuggestedQuestions } from "@/hooks/use-suggested-questions";
import { useWorkspaceInteractionStore } from "@/stores/workspace-interaction-store";

interface Props {
  workspaceId: string;
}

/**
 * Surfaces pre-computed questions as an exploration entry point in the Studio.
 * Questions are aggregated cross-sources, deduped server-side, capped at 8.
 * Clicking a question prefills the chat input via the workspace interaction store.
 */
export function SuggestedQuestionsBlock({ workspaceId }: Props) {
  const t = useTranslations("studio.suggestedQuestions");
  const { data: questions, isLoading } = useSuggestedQuestions(workspaceId);
  const setPrefill = useWorkspaceInteractionStore((s) => s.setPrefillChatMessage);

  if (isLoading) return <SkeletonBlock />;
  if (!questions || questions.length === 0) return null;

  return (
    <div className="vault-card rounded-xl border border-vault-border bg-vault-surface p-4">
      <div className="mb-3 flex items-center gap-2">
        <Sparkles className="h-3.5 w-3.5 text-vault-accent" />
        <h3 className="text-[12px] font-mono uppercase tracking-wider text-vault-text-muted">
          {t("title")}
        </h3>
      </div>
      <div className="space-y-1.5">
        {questions.map((q) => (
          <button
            key={`${q.source_id}-${q.question}`}
            type="button"
            onClick={() => setPrefill(q.question)}
            className="block w-full rounded-md px-3 py-2 text-left text-[13px]
                       text-vault-text-secondary transition-colors
                       hover:bg-vault-surface-active hover:text-vault-text"
          >
            <span className="block">{q.question}</span>
            <span className="mt-0.5 block truncate text-[11px] text-vault-text-muted">
              {q.source_name}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function SkeletonBlock() {
  return (
    <div className="vault-card rounded-xl border border-vault-border bg-vault-surface p-4">
      <div className="mb-3 h-3 w-32 rounded bg-vault-surface-active" />
      <div className="space-y-1.5">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-12 w-full rounded-md bg-vault-surface-active/60"
          />
        ))}
      </div>
    </div>
  );
}
