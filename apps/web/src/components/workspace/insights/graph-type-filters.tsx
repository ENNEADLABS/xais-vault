"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

export const ENTITY_TYPE_COLORS: Record<string, string> = {
  company: "#3b82f6",
  person: "#22c55e",
  metric: "#f97316",
  clause: "#a855f7",
  date: "#06b6d4",
  amount: "#10b981",
};

interface Props {
  entitiesByType: Record<string, number>;
  activeTypes: Set<string>;
  onToggle: (type: string) => void;
}

export function GraphTypeFilters({
  entitiesByType,
  activeTypes,
  onToggle,
}: Props) {
  const t = useTranslations("studio.graph.types");
  const types = Object.keys(entitiesByType).sort();

  return (
    <div className="flex items-center gap-1.5">
      {types.map((type) => {
        const active = activeTypes.size === 0 || activeTypes.has(type);
        const color = ENTITY_TYPE_COLORS[type] ?? "#9ca3af";
        return (
          <button
            key={type}
            type="button"
            onClick={() => onToggle(type)}
            className={cn(
              "flex items-center gap-1.5 rounded px-2 py-1 text-[11px] font-mono uppercase tracking-wider transition-colors",
              active
                ? "bg-vault-surface-active text-vault-text"
                : "text-vault-text-muted hover:bg-vault-surface-hover",
            )}
            title={`${entitiesByType[type]} ${type}`}
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: active ? color : undefined }}
            />
            {t(type, { default: type })}
            <span className="text-vault-text-muted">
              {entitiesByType[type]}
            </span>
          </button>
        );
      })}
    </div>
  );
}
