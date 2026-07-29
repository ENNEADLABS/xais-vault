"use client";

import { useTranslations } from "next-intl";
import { StickyNote, BarChart3, ClipboardList } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export type ChatAction = "note" | "briefing" | "summary";

interface ChatActionsBarProps {
  onAction: (action: ChatAction) => void;
  disabled?: boolean;
  className?: string;
}

const actions: { key: ChatAction; icon: LucideIcon; labelKey: string }[] = [
  { key: "note", icon: StickyNote, labelKey: "actionNote" },
  { key: "briefing", icon: BarChart3, labelKey: "actionBriefing" },
  { key: "summary", icon: ClipboardList, labelKey: "actionSummary" },
];

const btnClass =
  "border border-vault-border bg-transparent text-vault-text-secondary text-[13px] rounded-lg px-4 py-2 hover:bg-vault-surface-hover transition-colors duration-150";

export function ChatActionsBar({ onAction, disabled, className }: ChatActionsBarProps) {
  const t = useTranslations("chat");

  return (
    <div
      className={cn(
        "flex items-center justify-center gap-2 border-b border-vault-border py-2 px-4",
        className,
      )}
    >
      {actions.map(({ key, icon: Icon, labelKey }) => (
        <button
          key={key}
          type="button"
          disabled={disabled}
          className={cn(btnClass, disabled && "opacity-50 cursor-not-allowed")}
          onClick={() => onAction(key)}
        >
          <Icon className="mr-2 inline h-4 w-4" />
          {t(labelKey)}
        </button>
      ))}
    </div>
  );
}
