"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

interface WorkspacesEmptyStateProps {
  onCreateClick: () => void;
}

export function WorkspacesEmptyState({ onCreateClick }: WorkspacesEmptyStateProps) {
  const t = useTranslations("workspaces");

  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      {/* Illustration style blueprint/schéma technique */}
      <div className="mb-10 relative">
        <svg
          width="160"
          height="140"
          viewBox="0 0 160 140"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="text-vault-text-secondary/15"
          aria-hidden="true"
        >
          {/* Grille de fond */}
          <line x1="0" y1="20" x2="160" y2="20" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="0" y1="40" x2="160" y2="40" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="0" y1="60" x2="160" y2="60" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="0" y1="80" x2="160" y2="80" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="0" y1="100" x2="160" y2="100" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="0" y1="120" x2="160" y2="120" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="20" y1="0" x2="20" y2="140" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="40" y1="0" x2="40" y2="140" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="80" y1="0" x2="80" y2="140" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="120" y1="0" x2="120" y2="140" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="140" y1="0" x2="140" y2="140" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />

          {/* Card principale — bordure gauche colorée */}
          <rect x="30" y="30" width="100" height="68" rx="2" stroke="currentColor" strokeWidth="1.5" />
          <rect x="30" y="30" width="3" height="68" rx="1" fill="currentColor" opacity="0.4" />

          {/* Contenu simulé dans la card */}
          <rect x="42" y="42" width="28" height="5" rx="1" fill="currentColor" opacity="0.3" />
          <rect x="42" y="52" width="18" height="3" rx="1" fill="currentColor" opacity="0.2" />
          <rect x="42" y="62" width="56" height="3" rx="1" fill="currentColor" opacity="0.15" />
          <rect x="42" y="69" width="40" height="3" rx="1" fill="currentColor" opacity="0.15" />

          {/* Footer card */}
          <line x1="30" y1="83" x2="130" y2="83" stroke="currentColor" strokeWidth="1" opacity="0.4" />
          <rect x="38" y="88" width="20" height="3" rx="1" fill="currentColor" opacity="0.2" />
          <rect x="75" y="88" width="20" height="3" rx="1" fill="currentColor" opacity="0.2" />
          <rect x="112" y="88" width="10" height="3" rx="1" fill="currentColor" opacity="0.2" />

          {/* Croix centrale — "ajouter" */}
          <line x1="80" y1="112" x2="80" y2="132" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.5" />
          <line x1="70" y1="122" x2="90" y2="122" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.5" />
          <circle cx="80" cy="122" r="10" stroke="currentColor" strokeWidth="1.5" opacity="0.3" />

          {/* Coins de cadrage */}
          <path d="M8 18 L8 8 L18 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
          <path d="M152 18 L152 8 L142 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
          <path d="M8 122 L8 132 L18 132" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
          <path d="M152 122 L152 132 L142 132" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
        </svg>

        {/* Label terminal flottant */}
        <span className="absolute -bottom-2 left-1/2 -translate-x-1/2 font-mono text-[11px] tracking-widest text-vault-text-secondary/30 uppercase whitespace-nowrap">
          NO_RECORDS_FOUND
        </span>
      </div>

      <h2 className="mb-2 text-lg font-semibold text-vault-text">
        {t("emptyTitle")}
      </h2>
      <p className="mb-8 max-w-xs text-sm text-vault-text-secondary leading-relaxed">
        {t("emptyDescription")}
      </p>

      <Button
        onClick={onCreateClick}
        className="h-9 rounded-none bg-vault-accent text-vault-bg font-mono text-xs font-semibold uppercase tracking-wider hover:bg-vault-accent-hover active:scale-[0.98] transition-all"
      >
        <Plus className="mr-1.5 h-3.5 w-3.5" />
        {t("emptyAction")}
      </Button>
    </div>
  );
}
