"use client";

import { type KeyboardEvent } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { PRESET_TAGS, getTagColor } from "./tag-colors";

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder: string;
}

export function TagInput({
  value: tags,
  onChange,
  placeholder,
}: TagInputProps) {
  function togglePreset(label: string) {
    if (tags.includes(label)) {
      onChange(tags.filter((t) => t !== label));
    } else {
      onChange([...tags, label]);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    const input = e.currentTarget;
    if ((e.key === "Enter" || e.key === ",") && input.value.trim()) {
      e.preventDefault();
      const tag = input.value.trim().toLowerCase();
      if (!tags.includes(tag)) onChange([...tags, tag]);
      input.value = "";
    }
    if (e.key === "Backspace" && !input.value && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  }

  function removeTag(tag: string) {
    onChange(tags.filter((t) => t !== tag));
  }

  return (
    <div className="space-y-1.5">
      {/* Preset tags */}
      <div className="flex flex-wrap gap-1">
        {PRESET_TAGS.map(({ label, color }) => {
          const active = tags.includes(label);
          return (
            <button
              key={label}
              type="button"
              onClick={() => togglePreset(label)}
              className={cn(
                "rounded px-1.5 py-0.5 font-mono text-[11px] uppercase tracking-wide transition-all",
                active ? color : "bg-vault-border/20 text-vault-text-muted hover:bg-vault-border/40",
                active && "ring-1 ring-current/30",
              )}
            >
              #{label}
            </button>
          );
        })}
      </div>

      {/* Tags sélectionnés + input custom */}
      <div className="flex flex-wrap items-center gap-1 min-h-5">
        {tags.map((tag) => (
          <span
            key={tag}
            className={cn(
              "inline-flex items-center gap-0.5 rounded px-1.5 py-0 font-mono text-[11px] uppercase tracking-wide cursor-pointer hover:opacity-80 transition-opacity",
              getTagColor(tag),
            )}
            onClick={() => removeTag(tag)}
          >
            {tag}
            <X className="h-2.5 w-2.5" />
          </span>
        ))}
        <input
          type="text"
          onKeyDown={handleKeyDown}
          placeholder={tags.length === 0 ? placeholder : ""}
          className="flex-1 min-w-16 bg-transparent text-[11px] placeholder:text-muted-foreground/40 outline-none"
        />
      </div>
    </div>
  );
}
