import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  icon: React.ElementType;
  title: string;
  description?: string;
  label?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

/**
 * Empty state avec illustration blueprint technique.
 * Cohérent avec le style "vault dark" du projet.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  label,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
      <div className="relative mb-2">
        <svg
          width="96"
          height="80"
          viewBox="0 0 96 80"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="text-vault-text-secondary/12"
          aria-hidden="true"
        >
          {/* Grille de fond */}
          <line x1="0" y1="20" x2="96" y2="20" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="0" y1="40" x2="96" y2="40" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="0" y1="60" x2="96" y2="60" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="24" y1="0" x2="24" y2="80" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="48" y1="0" x2="48" y2="80" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          <line x1="72" y1="0" x2="72" y2="80" stroke="currentColor" strokeWidth="0.5" strokeDasharray="2 4" />
          {/* Coins de cadrage */}
          <path d="M4 12 L4 4 L12 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
          <path d="M92 12 L92 4 L84 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
          <path d="M4 68 L4 76 L12 76" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
          <path d="M92 68 L92 76 L84 76" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.4" />
        </svg>
        {/* Icône centrée par-dessus la grille */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="rounded-xl bg-vault-surface-active p-3">
            <Icon className="h-6 w-6 text-vault-text-muted/50" />
          </div>
        </div>
        {/* Label terminal */}
        {label && (
          <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 font-mono text-[9px] tracking-widest text-vault-text-secondary/25 uppercase whitespace-nowrap">
            {label}
          </span>
        )}
      </div>
      <div>
        <p className="text-sm font-medium text-vault-text">{title}</p>
        {description && (
          <p className="mt-1 max-w-xs text-xs text-vault-text-muted">
            {description}
          </p>
        )}
      </div>
      {action && (
        <Button
          variant="outline"
          size="sm"
          onClick={action.onClick}
          className="mt-1"
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}
