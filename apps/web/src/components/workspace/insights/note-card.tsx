"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Pin, FileText, AlertTriangle, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUpdateNote } from "@/lib/hooks/use-notes";
import { useSources } from "@/lib/hooks/use-sources";
import { useInsights } from "@/lib/hooks/use-insights";
import type { Note } from "@/types/api";
import { NoteEditor } from "./note-editor";
import { NoteCardActions } from "./note-card-actions";
import { getTagColor } from "./tag-colors";

interface NoteCardProps {
  note: Note;
  workspaceId: string;
}

export function NoteCard({ note, workspaceId }: NoteCardProps) {
  const t = useTranslations("notes");
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const updateNote = useUpdateNote(workspaceId);
  const { data: sourcesData } = useSources(workspaceId);
  const { data: findingsData } = useInsights(workspaceId, {});

  const linkedSource = note.linked_source_id
    ? sourcesData?.data?.find((s) => s.id === note.linked_source_id)
    : null;
  const linkedInsight = note.linked_insight_id
    ? findingsData?.data?.find((f) => f.id === note.linked_insight_id)
    : null;

  function handleChecklistToggle(index: number) {
    if (!note.checklist_items) return;
    const updated = note.checklist_items.map((item, i) =>
      i === index ? { ...item, checked: !item.checked } : item,
    );
    updateNote.mutate({
      noteId: note.id,
      update: { checklist_items: updated },
    });
  }

  if (editing) {
    return (
      <NoteEditor
        workspaceId={workspaceId}
        note={note}
        onClose={() => setEditing(false)}
      />
    );
  }

  return (
    <div className="vault-card rounded-xl border border-vault-border/50 bg-vault-surface p-3 space-y-2">
      <div className="flex items-start gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            {note.is_pinned && (
              <Pin className="h-3 w-3 shrink-0 text-vault-accent" />
            )}
            <span className="text-xs font-medium truncate">
              {note.title ?? t("untitled")}
            </span>
          </div>
        </div>

        <NoteCardActions
          note={note}
          workspaceId={workspaceId}
          onEdit={() => setEditing(true)}
        />
      </div>

      <p
        className={cn(
          "text-[14px] leading-relaxed text-muted-foreground cursor-pointer whitespace-pre-wrap font-reading",
          !expanded && "line-clamp-3",
        )}
        onClick={() => setExpanded((v) => !v)}
      >
        {note.content}
      </p>

      {note.checklist_items && note.checklist_items.length > 0 && (
        <ul className="space-y-1">
          {note.checklist_items.map((item, i) => (
            <li
              key={i}
              className="flex items-center gap-2 text-xs cursor-pointer"
              onClick={() => handleChecklistToggle(i)}
            >
              <span
                className={cn(
                  "h-3.5 w-3.5 shrink-0 rounded border border-vault-border/70 flex items-center justify-center",
                  item.checked && "bg-vault-accent border-vault-accent",
                )}
              >
                {item.checked && (
                  <svg
                    viewBox="0 0 10 10"
                    className="h-2 w-2 text-white fill-current"
                  >
                    <path
                      d="M1.5 5.5l2.5 2.5 4.5-5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      fill="none"
                      strokeLinecap="round"
                    />
                  </svg>
                )}
              </span>
              <span
                className={cn(
                  item.checked && "line-through text-muted-foreground/60",
                )}
              >
                {item.text}
              </span>
            </li>
          ))}
        </ul>
      )}

      {note.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {note.tags.map((tag) => (
            <span
              key={tag}
              className={cn(
                "rounded px-1.5 py-0 font-mono text-[11px] uppercase tracking-wide",
                getTagColor(tag),
              )}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Liens vers source, insight, message */}
      {(linkedSource || linkedInsight || note.linked_message_id) && (
        <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground/70">
          {linkedSource && (
            <span className="inline-flex items-center gap-1">
              <FileText className="h-3 w-3" />
              {linkedSource.name}
            </span>
          )}
          {linkedInsight && (
            <span className="inline-flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              {linkedInsight.title}
            </span>
          )}
          {note.linked_message_id && (
            <span className="inline-flex items-center gap-1 italic">
              <MessageSquare className="h-3 w-3" />
              {t("linkedMessage")}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
