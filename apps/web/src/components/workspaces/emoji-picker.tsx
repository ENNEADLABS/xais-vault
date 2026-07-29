"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { ICON_MAP } from "./workspace-icon";

const ICONS = Object.keys(ICON_MAP);

// Emojis fréquents pour le picker custom
const CUSTOM_EMOJIS = ["😀", "🏦", "💡", "🔍", "📈", "🌍", "🏭", "⭐", "🎯", "🔑", "💎", "🤝"];

interface EmojiPickerProps {
  selected: string;
  onSelect: (icon: string) => void;
  label: string;
}

export function EmojiPicker({ selected, onSelect, label }: EmojiPickerProps) {
  const [showCustom, setShowCustom] = useState(false);
  const isCustomSelected = selected.length <= 2 && !ICON_MAP[selected];

  return (
    <div className="space-y-1.5">
      <p className="font-mono text-[12px] uppercase tracking-wider text-vault-text-secondary mb-1.5">
        {label}
      </p>
      <div className="flex flex-wrap gap-2">
        {ICONS.map((key) => {
          const Icon = ICON_MAP[key];
          if (!Icon) return null;
          const isSelected = selected === key;
          return (
            <button
              key={key}
              type="button"
              onClick={() => { onSelect(key); setShowCustom(false); }}
              className={cn(
                "w-10 h-10 flex items-center justify-center rounded-lg",
                "border border-vault-border",
                "hover:border-vault-accent hover:bg-vault-accent-dim",
                "transition-colors duration-150",
                isSelected && "border-vault-accent bg-vault-accent-dim",
              )}
            >
              <Icon className="w-5 h-5" />
            </button>
          );
        })}
        {/* Bouton Autre... */}
        <button
          type="button"
          onClick={() => setShowCustom((v) => !v)}
          className={cn(
            "w-10 h-10 flex items-center justify-center rounded-lg",
            "border border-vault-border text-vault-text-muted text-[13px]",
            "hover:border-vault-accent hover:bg-vault-accent-dim",
            "transition-colors duration-150",
            (showCustom || isCustomSelected) && "border-vault-accent bg-vault-accent-dim",
          )}
          title="Emoji personnalisé"
        >
          {isCustomSelected ? selected : "···"}
        </button>
      </div>

      {/* Grille emoji custom */}
      {showCustom && (
        <div className="flex flex-wrap gap-2 pt-1">
          {CUSTOM_EMOJIS.map((emoji) => (
            <button
              key={emoji}
              type="button"
              onClick={() => { onSelect(emoji); setShowCustom(false); }}
              className={cn(
                "w-10 h-10 flex items-center justify-center rounded-lg text-lg",
                "border border-vault-border",
                "hover:border-vault-accent hover:bg-vault-accent-dim",
                "transition-colors duration-150",
                selected === emoji && "border-vault-accent bg-vault-accent-dim",
              )}
            >
              {emoji}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
