"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FileText, Sheet, Presentation, FileCode, ChevronDown } from "lucide-react";
import { cn, formatFileSize } from "@/lib/utils";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { SourceCardDetails } from "./source-card-details";
import type { Source } from "@/types/api";
import type { LucideIcon } from "lucide-react";

const TYPE_CONFIG: Record<string, { icon: LucideIcon; colorClass: string }> = {
  pdf: { icon: FileText, colorClass: "text-file-pdf" },
  docx: { icon: FileText, colorClass: "text-file-docx" },
  xlsx: { icon: Sheet, colorClass: "text-file-xlsx" },
  pptx: { icon: Presentation, colorClass: "text-file-pptx" },
  txt: { icon: FileCode, colorClass: "text-file-txt" },
  md: { icon: FileCode, colorClass: "text-file-txt" },
  csv: { icon: FileCode, colorClass: "text-file-txt" },
};

const STATUS_CLASSES: Record<string, string> = {
  pending: "bg-vault-warning-dim text-vault-warning",
  processing:
    "bg-vault-accent/15 text-vault-accent animate-[vault-pulse_1.5s_ease-in-out_infinite]",
  ready: "bg-vault-success/15 text-vault-success",
  failed: "bg-vault-danger/15 text-vault-danger",
};

interface SourceCardProps {
  source: Source;
}

export function SourceCard({ source }: SourceCardProps) {
  const t = useTranslations("workspace_page");
  const [expanded, setExpanded] = useState(false);

  const config = TYPE_CONFIG[source.type] ?? {
    icon: FileText,
    colorClass: "text-muted-foreground",
  };
  const Icon = config.icon;

  const statusLabel: Record<string, string> = {
    pending: t("statusPending"),
    processing: t("statusProcessing"),
    ready: t("statusReady"),
    failed: t("statusFailed"),
  };

  const hasDetails = Boolean(
    source.status === "ready" &&
      (source.summary || source.topics?.length || source.suggested_questions?.length),
  );

  return (
    <div
      className={cn(
        "rounded-lg border transition-all duration-200",
        expanded
          ? "border-vault-border-active bg-vault-surface"
          : "border-transparent hover:bg-vault-surface-active",
      )}
    >
      {/* Header — toujours visible */}
      <button
        type="button"
        onClick={() => hasDetails && setExpanded(!expanded)}
        className={cn(
          "flex w-full items-center gap-2 p-2.5 text-left",
          hasDetails && "cursor-pointer",
        )}
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-vault-surface-active">
          <Icon className={cn("h-4 w-4", config.colorClass)} />
        </div>
        <div className="min-w-0 flex-1">
          <Tooltip>
            <TooltipTrigger
              render={<p className="truncate text-sm font-medium" />}
            >
              {source.name}
            </TooltipTrigger>
            <TooltipContent>{source.name}</TooltipContent>
          </Tooltip>
          <div className="mt-0.5 flex items-center gap-1.5">
            <span
              className={cn(
                "inline-flex rounded px-1.5 py-px text-xs font-medium",
                STATUS_CLASSES[source.status] ?? STATUS_CLASSES.pending,
              )}
            >
              {statusLabel[source.status] ?? source.status}
            </span>
            <span className="text-xs text-vault-text-muted">
              {formatFileSize(source.file_size_bytes)}
            </span>
          </div>
        </div>
        {hasDetails && (
          <ChevronDown
            className={cn(
              "h-4 w-4 shrink-0 text-vault-text-muted transition-transform duration-200",
              expanded && "rotate-180",
            )}
          />
        )}
      </button>

      {/* Expanded details */}
      <div
        className={cn(
          "grid transition-all duration-200",
          expanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="overflow-hidden">
          <SourceCardDetails source={source} />
        </div>
      </div>
    </div>
  );
}
