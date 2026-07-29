"use client";

import { useTranslations } from "next-intl";
import { FileText } from "lucide-react";
import { useWorkspaceInteractionStore } from "@/stores/workspace-interaction-store";
import { usePanelStore } from "@/stores/panel-store";
import type { Citation } from "@/types/api";

interface CitationBadgeProps {
  citation: Citation;
  onClick?: () => void;
}

export function CitationBadge({ citation, onClick }: CitationBadgeProps) {
  const t = useTranslations("chat");
  const setHighlightSource = useWorkspaceInteractionStore(
    (s) => s.setHighlightSource,
  );
  const setScrollToSourceId = useWorkspaceInteractionStore((s) => s.setScrollToSourceId);
  const leftCollapsed = usePanelStore((s) => s.leftCollapsed);
  const toggleLeft = usePanelStore((s) => s.toggleLeft);

  const label = citation.page_number
    ? `${citation.source_name} ${t("citationPage", { page: citation.page_number })}`
    : citation.source_name;

  function handleClick() {
    // Expand le panneau gauche s'il est collapsed
    if (leftCollapsed) toggleLeft();
    // Highlight temporaire + scroll to source
    setHighlightSource(citation.source_id, citation.page_number ?? undefined);
    setScrollToSourceId(citation.source_id);
    // Callback custom si fourni
    onClick?.();
  }

  return (
    <button
      className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-mono bg-vault-accent-dim text-vault-accent rounded transition-colors hover:bg-vault-accent/20 cursor-pointer"
      title={citation.quote}
      onClick={handleClick}
    >
      <FileText className="h-3 w-3 shrink-0" />
      <span className="max-w-[140px] truncate">{label}</span>
    </button>
  );
}
