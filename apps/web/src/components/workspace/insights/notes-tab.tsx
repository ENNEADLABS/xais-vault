"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { StickyNote, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useNotes } from "@/lib/hooks/use-notes";
import { NoteCard } from "./note-card";
import { NoteEditor } from "./note-editor";

interface NotesTabProps {
  workspaceId: string;
}

export function NotesTab({ workspaceId }: NotesTabProps) {
  const t = useTranslations("notes");
  const { data, isLoading } = useNotes(workspaceId);
  const notes = data?.data ?? [];
  const [creating, setCreating] = useState(false);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="shrink-0 flex items-center justify-between px-3 py-2 border-b border-vault-border/30">
        <span className="text-xs text-muted-foreground">
          {notes.length > 0
            ? `${notes.length} note${notes.length > 1 ? "s" : ""}`
            : ""}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 gap-1 text-xs"
          onClick={() => setCreating(true)}
        >
          <Plus className="h-3.5 w-3.5" />
          {t("newNote")}
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {creating && (
          <NoteEditor workspaceId={workspaceId} onClose={() => setCreating(false)} />
        )}

        {isLoading ? (
          <>
            <Skeleton className="h-20 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
          </>
        ) : notes.length === 0 && !creating ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 py-12">
            <StickyNote className="h-8 w-8 text-vault-text-muted" />
            <p className="font-mono text-[13px] text-vault-text-secondary uppercase tracking-wide">{t("noNotes")}</p>
            <p className="text-[12px] text-vault-text-muted text-center">{t("noNotesHint")}</p>
          </div>
        ) : (
          notes.map((note) => (
            <NoteCard key={note.id} note={note} workspaceId={workspaceId} />
          ))
        )}
      </div>
    </div>
  );
}
