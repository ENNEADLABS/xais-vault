"use client";

import { useTranslations } from "next-intl";
import { Plus, PanelLeftOpen } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SourcesPanelHeaderProps {
  sourceCount: number;
  isLoading: boolean;
  typeBreakdown: string;
  totalPages: number;
  totalWords: number;
  onUpload: () => void;
  onCollapse?: () => void;
}

export function SourcesPanelHeader({
  sourceCount,
  isLoading,
  typeBreakdown,
  totalPages,
  totalWords,
  onUpload,
  onCollapse,
}: SourcesPanelHeaderProps) {
  const t = useTranslations("workspace_page");

  return (
    <div className="shrink-0 border-b border-vault-border bg-vault-surface px-3">
      <div className="flex h-11 items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-mono text-xs uppercase tracking-widest text-vault-text-muted">
            {t("sources")}
          </h3>
          {!isLoading && (
            <span className="rounded bg-vault-accent-dim px-1.5 py-0.5 font-mono text-[11px] text-vault-accent">
              {sourceCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-vault-accent hover:bg-vault-accent/10 hover:text-vault-accent"
            onClick={onUpload}
            title={t("uploadSource")}
          >
            <Plus className="h-4 w-4" />
          </Button>
          {onCollapse && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onCollapse}
              aria-label="Fermer Sources"
            >
              <PanelLeftOpen className="h-3.5 w-3.5 rotate-180" />
            </Button>
          )}
        </div>
      </div>

      {/* Stats agrégées */}
      {!isLoading && sourceCount > 0 && (
        <div className="pb-2 text-[11px] text-vault-text-muted">
          <span>{typeBreakdown}</span>
          {(totalPages > 0 || totalWords > 0) && (
            <span>
              {" · "}
              {totalPages > 0 && t("sourcePages", { count: totalPages })}
              {totalPages > 0 && totalWords > 0 && " · "}
              {totalWords > 0 &&
                t("sourceWords", { count: totalWords.toLocaleString() })}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
