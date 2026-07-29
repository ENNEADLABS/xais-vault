"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  BarChart3,
  BookOpen,
  HelpCircle,
  Loader2,
  Scale,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface SmartPrompt {
  label: string;
  prompt: string;
  icon: LucideIcon;
  disabled?: boolean;
}

export interface WorkspaceContext {
  sourceCount: number;
  processingCount: number;
  readyCount: number;
  scanStatus: string;
  insightsCount: number;
  criticalCount: number;
  investigationCount: number;
}

interface SmartPromptsBarProps {
  context: WorkspaceContext;
  onPrompt: (prompt: string) => void;
  disabled?: boolean;
  className?: string;
}

function getSmartPrompts(
  context: WorkspaceContext,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  t: (key: string, values?: Record<string, any>) => string,
): SmartPrompt[] {
  const prompts: SmartPrompt[] = [];

  // Aucune source → guide l'utilisateur
  if (context.sourceCount === 0) {
    prompts.push({
      label: t("smartPrompts.howToStart"),
      prompt: t("smartPrompts.howToStartPrompt"),
      icon: HelpCircle,
    });
  }

  // Sources en cours d'indexation
  if (context.processingCount > 0) {
    prompts.push({
      label: t("smartPrompts.processingLabel", {
        count: context.processingCount,
      }),
      prompt: "",
      icon: Loader2,
      disabled: true,
    });
  }

  // Scan terminé avec insights
  if (context.scanStatus === "scanned" && context.insightsCount > 0) {
    prompts.push({
      label: t("smartPrompts.redFlags"),
      prompt: t("smartPrompts.redFlagsPrompt"),
      icon: AlertTriangle,
    });
    prompts.push({
      label: t("smartPrompts.scanSummary"),
      prompt: t("smartPrompts.scanSummaryPrompt"),
      icon: BookOpen,
    });
  }

  // Investigations terminées
  if (context.investigationCount > 0) {
    prompts.push({
      label: t("smartPrompts.investigations"),
      prompt: t("smartPrompts.investigationsPrompt"),
      icon: Search,
    });
  }

  // Toujours disponibles (si on a des sources ready)
  if (context.readyCount > 0) {
    prompts.push({
      label: t("smartPrompts.metrics"),
      prompt: t("smartPrompts.metricsPrompt"),
      icon: BarChart3,
    });
    prompts.push({
      label: t("smartPrompts.strengths"),
      prompt: t("smartPrompts.strengthsPrompt"),
      icon: Scale,
    });
  }

  return prompts.slice(0, 4);
}

const chipClass =
  "inline-flex items-center gap-1.5 whitespace-nowrap border border-vault-border bg-transparent text-vault-text-secondary text-[12px] rounded-full px-3 py-1.5 hover:bg-vault-surface-hover hover:text-vault-text transition-colors duration-150 cursor-pointer";

export function SmartPromptsBar({
  context,
  onPrompt,
  disabled,
  className,
}: SmartPromptsBarProps) {
  const t = useTranslations("chat");

  const prompts = useMemo(
    () => getSmartPrompts(context, t),
    [context, t],
  );

  if (prompts.length === 0) return null;

  return (
    <div
      className={cn(
        "flex items-center gap-2 overflow-x-auto border-b border-vault-border py-2 px-4 scrollbar-none",
        className,
      )}
    >
      {prompts.map(({ label, prompt, icon: Icon, disabled: promptDisabled }) => (
        <button
          key={label}
          type="button"
          disabled={disabled || promptDisabled}
          className={cn(
            chipClass,
            (disabled || promptDisabled) && "opacity-50 cursor-not-allowed",
            promptDisabled && "animate-pulse",
          )}
          onClick={() => onPrompt(prompt)}
        >
          <Icon className="h-3.5 w-3.5 shrink-0" />
          {label}
        </button>
      ))}
    </div>
  );
}
