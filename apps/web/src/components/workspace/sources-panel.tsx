"use client";

import { useState, useMemo, useCallback } from "react";
import { useTranslations } from "next-intl";
import { FolderOpen, Search, Upload } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { useSources } from "@/lib/hooks/use-sources";
import { useDragDrop } from "@/hooks/use-drag-drop";
import { cn } from "@/lib/utils";
import { SourceCard } from "./source-card";
import { SourceCardSkeleton } from "./source-card-skeleton";
import { SourceUploadDialog } from "./source-upload-dialog";
import { SourcesPanelCollapsed } from "./sources-panel-collapsed";
import { SourcesPanelHeader } from "./sources-panel-header";
import type { Source } from "@/types/api";

const EMPTY_SOURCES: Source[] = [];

interface SourcesPanelProps {
  workspaceId: string;
  collapsed?: boolean;
  onCollapse?: () => void;
}

/** Compte par type de fichier */
function buildTypeBreakdown(sources: Array<{ type: string }>) {
  const counts: Record<string, number> = {};
  for (const s of sources) {
    const ext = s.type.toUpperCase();
    counts[ext] = (counts[ext] ?? 0) + 1;
  }
  return Object.entries(counts)
    .map(([ext, count]) => `${count} ${ext}`)
    .join(" · ");
}

export function SourcesPanel({
  workspaceId,
  collapsed,
  onCollapse,
}: SourcesPanelProps) {
  const t = useTranslations("workspace_page");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [droppedFiles, setDroppedFiles] = useState<File[]>([]);
  const [search, setSearch] = useState("");
  const { data, isLoading } = useSources(workspaceId);
  const sources = data?.data ?? EMPTY_SOURCES;

  const handleDroppedFiles = useCallback((files: File[]) => {
    setDroppedFiles(files);
    setDialogOpen(true);
  }, []);

  const { isDragging, dragHandlers } = useDragDrop({ onFiles: handleDroppedFiles });

  // Filtrage client
  const filtered = useMemo(() => {
    if (!search.trim()) return sources;
    const q = search.toLowerCase();
    return sources.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.summary?.toLowerCase().includes(q),
    );
  }, [sources, search]);

  // Stats agrégées
  const totalPages = useMemo(
    () => sources.reduce((sum, s) => sum + (s.page_count ?? 0), 0),
    [sources],
  );
  const totalWords = useMemo(
    () => sources.reduce((sum, s) => sum + (s.word_count ?? 0), 0),
    [sources],
  );
  const typeBreakdown = useMemo(() => buildTypeBreakdown(sources), [sources]);

  function handleDialogChange(open: boolean) {
    setDialogOpen(open);
    if (!open) setDroppedFiles([]);
  }

  // ─── Collapsed view ─────────────────────────────────────
  if (collapsed) {
    return (
      <>
        <SourcesPanelCollapsed
          sources={sources}
          onExpand={onCollapse}
          onUpload={() => setDialogOpen(true)}
        />
        <SourceUploadDialog
          open={dialogOpen}
          onOpenChange={handleDialogChange}
          workspaceId={workspaceId}
          initialFiles={droppedFiles}
        />
      </>
    );
  }

  // ─── Full view ───────────────────────────────────────────
  return (
    <div
      className={cn(
        "relative flex h-full flex-col overflow-hidden transition-colors",
        isDragging && "ring-2 ring-inset ring-vault-accent bg-vault-accent/5",
      )}
      {...dragHandlers}
    >
      {/* Drag overlay */}
      {isDragging && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-vault-accent/5">
          <div className="flex flex-col items-center gap-2 rounded-xl border-2 border-dashed border-vault-accent bg-vault-surface/90 px-8 py-6">
            <Upload className="h-8 w-8 text-vault-accent" />
            <p className="text-sm font-medium text-vault-accent">
              {t("dropFilesHere")}
            </p>
          </div>
        </div>
      )}

      <SourcesPanelHeader
        sourceCount={sources.length}
        isLoading={isLoading}
        typeBreakdown={typeBreakdown}
        totalPages={totalPages}
        totalWords={totalWords}
        onUpload={() => setDialogOpen(true)}
        onCollapse={onCollapse}
      />

      {/* Search bar */}
      {sources.length > 0 && (
        <div className="shrink-0 px-3 py-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-vault-text-muted" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("searchSources")}
              className="w-full rounded-md border border-vault-border bg-vault-bg py-1.5 pl-8 pr-2 text-[13px] text-vault-text placeholder:text-vault-text-muted outline-none transition-colors focus:border-vault-accent"
            />
          </div>
        </div>
      )}

      {/* Upload button */}
      {sources.length === 0 && !isLoading && (
        <div className="px-3 py-2">
          <button
            onClick={() => setDialogOpen(true)}
            className="w-full rounded-lg border border-dashed border-vault-border py-2.5 text-[13px] text-vault-text-muted transition-colors hover:border-vault-border-active hover:bg-vault-surface-hover hover:text-vault-text-secondary"
          >
            {t("uploadSource")}
          </button>
        </div>
      )}

      {/* Source list */}
      <div className="flex-1 overflow-y-auto px-3">
        {isLoading ? (
          <div className="space-y-1">
            <SourceCardSkeleton />
            <SourceCardSkeleton />
            <SourceCardSkeleton />
          </div>
        ) : sources.length === 0 ? (
          <EmptyState
            icon={FolderOpen}
            title={t("noSources")}
            description={t("noSourcesHint")}
            label="NO_SOURCES"
          />
        ) : filtered.length === 0 ? (
          <p className="py-4 text-center text-[13px] text-vault-text-muted">
            {t("noSearchResults")}
          </p>
        ) : (
          <div className="space-y-1 pb-4">
            {filtered.map((source) => (
              <SourceCard key={source.id} source={source} />
            ))}
          </div>
        )}
      </div>

      <SourceUploadDialog
        open={dialogOpen}
        onOpenChange={handleDialogChange}
        workspaceId={workspaceId}
        initialFiles={droppedFiles}
      />
    </div>
  );
}
