"use client";

import { useTranslations } from "next-intl";
import { X, MessageSquare } from "lucide-react";

interface Node {
  id: string;
  name: string;
  type: string;
  color: string;
  mentions: number;
  description: string | null;
}

interface Props {
  node: Node;
  onClose: () => void;
  onAsk: (name: string) => void;
}

export function GraphNodeDetail({ node, onClose, onAsk }: Props) {
  const t = useTranslations("studio.graph");
  return (
    <div className="absolute right-3 top-3 w-72 rounded-lg border border-vault-border bg-vault-surface p-3 shadow-xl">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className="h-3 w-3 rounded-full"
            style={{ backgroundColor: node.color }}
          />
          <span className="font-mono text-[10px] uppercase tracking-wider text-vault-text-muted">
            {node.type}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-0.5 text-vault-text-muted hover:bg-vault-surface-hover"
          aria-label={t("close")}
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <h4 className="mb-2 text-[14px] font-medium text-vault-text">
        {node.name}
      </h4>
      {node.description && (
        <p className="mb-2 text-[12px] text-vault-text-secondary">
          {node.description}
        </p>
      )}
      <p className="mb-3 text-[11px] text-vault-text-muted">
        {t("mentionCount", { count: node.mentions })}
      </p>
      <button
        type="button"
        onClick={() => onAsk(node.name)}
        className="flex w-full items-center justify-center gap-1.5 rounded-md bg-vault-accent/15 px-3 py-2 text-[12px] text-vault-accent transition-colors hover:bg-vault-accent/25"
      >
        <MessageSquare className="h-3.5 w-3.5" />
        {t("askAboutButton")}
      </button>
    </div>
  );
}
