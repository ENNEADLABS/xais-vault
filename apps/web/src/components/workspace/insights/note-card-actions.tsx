"use client";

import { useTranslations } from "next-intl";
import { Pin, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useUpdateNote, useDeleteNote } from "@/lib/hooks/use-notes";
import type { Note } from "@/types/api";

interface NoteCardActionsProps {
  note: Note;
  workspaceId: string;
  onEdit: () => void;
}

export function NoteCardActions({
  note,
  workspaceId,
  onEdit,
}: NoteCardActionsProps) {
  const t = useTranslations("notes");
  const updateNote = useUpdateNote(workspaceId);
  const deleteNote = useDeleteNote(workspaceId);

  function handleTogglePin() {
    updateNote.mutate({
      noteId: note.id,
      update: { is_pinned: !note.is_pinned },
    });
  }

  function handleDelete() {
    if (!confirm(t("deleteConfirm"))) return;
    deleteNote.mutate(note.id, {
      onSuccess: () => toast.success(t("noteDeleted")),
    });
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded p-0.5 text-muted-foreground/60 hover:bg-vault-surface-active hover:text-muted-foreground">
        <MoreHorizontal className="h-3 w-3" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={onEdit}>
          <Pencil className="mr-2 h-3.5 w-3.5" />
          {t("edit")}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleTogglePin}>
          <Pin className="mr-2 h-3.5 w-3.5" />
          {note.is_pinned ? t("unpin") : t("pin")}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={handleDelete}
          className="text-destructive focus:text-destructive"
        >
          <Trash2 className="mr-2 h-3.5 w-3.5" />
          {t("delete")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
