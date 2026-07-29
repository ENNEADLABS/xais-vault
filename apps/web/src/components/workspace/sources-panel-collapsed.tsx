"use client";

import { useTranslations } from "next-intl";
import { Plus, FolderOpen, PanelLeftOpen } from "lucide-react";
import type { Source } from "@/types/api";

interface SourcesPanelCollapsedProps {
  sources: Source[];
  onExpand?: () => void;
  onUpload: () => void;
}

export function SourcesPanelCollapsed({
  sources,
  onExpand,
  onUpload,
}: SourcesPanelCollapsedProps) {
  const t = useTranslations("workspace_page");

  return (
    <div className="flex h-full w-full flex-col items-center overflow-hidden border-r border-vault-border bg-vault-bg py-4">
      <button
        onClick={onExpand}
        className="mb-4 rounded p-1.5 transition-colors hover:bg-vault-surface-hover"
      >
        <PanelLeftOpen className="h-4 w-4 text-vault-text-muted" />
      </button>
      <span className="mb-4 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted [writing-mode:vertical-lr] rotate-180">
        {t("sources")}
      </span>
      <div className="mt-2 flex flex-col gap-2">
        {sources.slice(0, 5).map((s) => (
          <FolderOpen
            key={s.id}
            className="h-4 w-4 text-vault-text-muted"
          />
        ))}
      </div>
      <button
        onClick={onUpload}
        className="mt-auto rounded p-1.5 transition-colors hover:bg-vault-surface-hover"
      >
        <Plus className="h-4 w-4 text-vault-text-muted" />
      </button>
    </div>
  );
}
