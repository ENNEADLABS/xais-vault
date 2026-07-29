"use client";

import { useTranslations } from "next-intl";
import { Crosshair, X } from "lucide-react";
import { useWorkspaceInteractionStore } from "@/stores/workspace-interaction-store";

export function FocusSourceIndicator() {
  const t = useTranslations("chat");
  const focusSourceName = useWorkspaceInteractionStore((s) => s.focusSourceName);
  const clearFocusSource = useWorkspaceInteractionStore((s) => s.clearFocusSource);

  if (!focusSourceName) return null;

  return (
    <div className="flex items-center gap-2 border-b border-vault-accent/20 bg-vault-accent/5 px-4 py-1.5 text-[12px] text-vault-accent">
      <Crosshair className="h-3.5 w-3.5 shrink-0" />
      <span className="flex-1 truncate font-medium">
        {t("focusSource", { name: focusSourceName })}
      </span>
      <button
        type="button"
        onClick={clearFocusSource}
        className="rounded p-0.5 hover:bg-vault-accent/10 transition-colors"
        aria-label={t("focusClear")}
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
