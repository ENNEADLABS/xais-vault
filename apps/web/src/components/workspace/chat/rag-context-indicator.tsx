"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FileText, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RagContext } from "@/lib/hooks/use-send-message";

interface RagContextIndicatorProps {
  context: RagContext;
}

export function RagContextIndicator({ context }: RagContextIndicatorProps) {
  const t = useTranslations("chat.ragContext");
  const [expanded, setExpanded] = useState(false);

  if (context.chunkCount === 0) return null;

  const similarityColor =
    context.avgSimilarity >= 0.8
      ? "text-green-400"
      : context.avgSimilarity >= 0.65
        ? "text-yellow-400"
        : "text-red-400";

  // Pourcentage d'utilisation du budget tokens
  const tokensPct =
    context.tokensBudget > 0
      ? Math.round((context.tokensUsed / context.tokensBudget) * 100)
      : 0;

  // Couleur de la barre selon l'utilisation
  const tokenBarColor =
    tokensPct >= 90
      ? "bg-red-400"
      : tokensPct >= 70
        ? "bg-yellow-400"
        : "bg-green-400";

  return (
    <div className="mt-1 max-w-[85%]">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] text-vault-text-muted transition-colors hover:bg-vault-surface hover:text-vault-text-secondary"
      >
        <FileText className="h-3 w-3" />
        <span>
          {t("summary", {
            sources: context.sourceCount,
            passages: context.chunkCount,
          })}
        </span>
        <span className={cn("font-mono", similarityColor)}>
          {Math.round(context.avgSimilarity * 100)}%
        </span>
        <ChevronDown
          className={cn(
            "h-3 w-3 transition-transform",
            expanded && "rotate-180",
          )}
        />
      </button>

      {expanded && (
        <div className="mt-1 space-y-1.5 rounded-md border border-vault-border/50 bg-vault-surface px-2.5 py-1.5">
          {/* Barre d'utilisation tokens */}
          {context.tokensBudget > 0 && (
            <div className="space-y-0.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-vault-text-muted">Tokens</span>
                <span className="font-mono text-vault-text-secondary">
                  {context.tokensUsed.toLocaleString()} / {context.tokensBudget.toLocaleString()}
                  <span className="ml-1 text-vault-text-muted">({tokensPct}%)</span>
                </span>
              </div>
              <div className="h-1 w-full rounded-full bg-vault-border/50">
                <div
                  className={cn("h-1 rounded-full transition-all", tokenBarColor)}
                  style={{ width: `${Math.min(tokensPct, 100)}%` }}
                />
              </div>
            </div>
          )}

          {/* Liste des sources */}
          {context.sourcesUsed.map((source) => (
            <div
              key={source.id}
              className="flex items-center justify-between text-[11px]"
            >
              <span className="truncate text-vault-text-secondary">
                {source.name}
              </span>
              <span className="ml-2 shrink-0 font-mono text-vault-text-muted">
                {source.chunk_count} {t("chunks")}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
