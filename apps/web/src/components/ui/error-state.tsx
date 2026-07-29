"use client";

import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({ title, message, onRetry, className }: ErrorStateProps) {
  const t = useTranslations("common");

  return (
    <div className={cn("flex flex-col items-center justify-center gap-3 py-12", className)}>
      <AlertTriangle className="h-8 w-8 text-vault-danger" />
      <p className="font-mono text-[13px] uppercase tracking-wide text-vault-text-secondary">
        {title ?? t("errorTitle")}
      </p>
      <p className="max-w-xs text-center text-[13px] text-vault-text-muted">
        {message ?? t("errorMessage")}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 border border-vault-border bg-transparent px-4 py-2 font-mono text-[12px] uppercase text-vault-text-secondary transition-colors duration-150 hover:bg-vault-surface-hover"
        >
          {t("retry")}
        </button>
      )}
    </div>
  );
}
