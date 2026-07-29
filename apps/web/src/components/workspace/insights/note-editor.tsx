"use client";

import { useState, useRef, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Pin } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useCreateNote, useUpdateNote } from "@/lib/hooks/use-notes";
import type { Note } from "@/types/api";
import { TagInput } from "./tag-input";

interface NoteEditorProps {
  workspaceId: string;
  note?: Note;
  prefillContent?: string;
  linkedMessageId?: string;
  linkedInsightId?: string;
  onClose: () => void;
}

export function NoteEditor({
  workspaceId,
  note,
  prefillContent,
  linkedMessageId,
  linkedInsightId,
  onClose,
}: NoteEditorProps) {
  const t = useTranslations("notes");
  const createNote = useCreateNote(workspaceId);
  const updateNote = useUpdateNote(workspaceId);

  const [title, setTitle] = useState(note?.title ?? "");
  const [content, setContent] = useState(note?.content ?? prefillContent ?? "");
  const [tags, setTags] = useState<string[]>(note?.tags ?? []);
  const [isPinned, setIsPinned] = useState(note?.is_pinned ?? false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  function autoResize() {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${el.scrollHeight}px`;
    }
  }

  async function handleSubmit() {
    if (!content.trim()) return;

    const payload = {
      title: title.trim() || undefined,
      content: content.trim(),
      tags,
      is_pinned: isPinned,
      linked_message_id:
        linkedMessageId ?? note?.linked_message_id ?? undefined,
      linked_insight_id:
        linkedInsightId ?? note?.linked_insight_id ?? undefined,
    };

    if (note) {
      updateNote.mutate(
        { noteId: note.id, update: payload },
        {
          onSuccess: () => {
            toast.success(t("noteSaved"));
            onClose();
          },
        },
      );
    } else {
      createNote.mutate(payload, {
        onSuccess: () => {
          toast.success(t("noteSaved"));
          onClose();
        },
      });
    }
  }

  const isPending = createNote.isPending || updateNote.isPending;

  return (
    <div className="rounded-xl border border-vault-accent/30 bg-vault-surface p-3 space-y-2">
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder={t("titlePlaceholder")}
        className="w-full bg-transparent text-xs font-medium placeholder:text-muted-foreground/50 outline-none"
      />

      <textarea
        ref={textareaRef}
        value={content}
        onChange={(e) => {
          setContent(e.target.value);
          autoResize();
        }}
        placeholder={t("contentPlaceholder")}
        rows={3}
        className="w-full resize-none bg-transparent text-xs text-muted-foreground placeholder:text-muted-foreground/50 outline-none"
      />

      <TagInput
        value={tags}
        onChange={setTags}
        placeholder={t("tagsPlaceholder")}
      />

      <div className="flex items-center justify-between pt-1 border-t border-vault-border/30">
        <button
          type="button"
          onClick={() => setIsPinned((v) => !v)}
          className={cn(
            "flex items-center gap-1 text-[11px] transition-colors",
            isPinned
              ? "text-vault-accent"
              : "text-muted-foreground/60 hover:text-muted-foreground",
          )}
        >
          <Pin className="h-3 w-3" />
          {t("pin")}
        </button>

        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs"
            onClick={onClose}
          >
            {t("cancel")}
          </Button>
          <Button
            size="sm"
            className="h-6 text-xs"
            onClick={handleSubmit}
            disabled={!content.trim() || isPending}
          >
            {t("save")}
          </Button>
        </div>
      </div>
    </div>
  );
}
