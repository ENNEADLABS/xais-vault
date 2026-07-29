"use client";

import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { MoreHorizontal } from "lucide-react";
import {
  useRevokeApiKey,
  useRotateApiKey,
  useUpdateApiKey,
} from "@/lib/hooks/use-api-keys";
import type { ApiKey } from "@/types/api";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ApiKeyRowProps {
  apiKey: ApiKey;
  onRotated: (key: string) => void;
}

function formatRelativeTime(dateStr: string | null): string | null {
  if (!dateStr) return null;
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}j`;
}

export function ApiKeyRow({ apiKey, onRotated }: ApiKeyRowProps) {
  const t = useTranslations("settings");
  const revokeKey = useRevokeApiKey();
  const rotateKey = useRotateApiKey();
  const updateKey = useUpdateApiKey(apiKey.id);

  async function handleRevoke() {
    if (!confirm(t("apiKeys.revokeConfirm"))) return;
    try {
      await revokeKey.mutateAsync(apiKey.id);
      toast.success(t("apiKeys.revoked"));
    } catch {
      toast.error("Erreur lors de la révocation");
    }
  }

  async function handleRotate() {
    if (!confirm(t("apiKeys.rotateConfirm"))) return;
    try {
      const result = await rotateKey.mutateAsync(apiKey.id);
      if (result.data?.key) onRotated(result.data.key);
    } catch {
      toast.error("Erreur lors de la rotation");
    }
  }

  async function handleToggleActive() {
    try {
      await updateKey.mutateAsync({ is_active: !apiKey.is_active });
    } catch {
      toast.error("Erreur lors de la mise à jour");
    }
  }

  const relativeTime = formatRelativeTime(apiKey.last_used_at);

  return (
    <div className="flex items-center justify-between py-3 border-b last:border-0">
      <div className="space-y-0.5 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{apiKey.name}</span>
          <span className={cn("rounded px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide", apiKey.is_active ? "bg-vault-success-dim text-vault-success" : "bg-vault-border/40 text-vault-text-muted")}>
            {apiKey.is_active ? t("apiKeys.active") : t("apiKeys.inactive")}
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs text-vault-text-muted">
          <span className="font-mono">{apiKey.key_prefix}...</span>
          <span>
            {relativeTime
              ? t("apiKeys.lastUsed", { time: relativeTime })
              : t("apiKeys.neverUsed")}
          </span>
        </div>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
          <MoreHorizontal className="h-4 w-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={handleToggleActive}>
            {apiKey.is_active ? t("apiKeys.revoke") : t("apiKeys.active")}
          </DropdownMenuItem>
          {apiKey.is_active && (
            <DropdownMenuItem onClick={handleRotate}>
              {t("apiKeys.rotate")}
            </DropdownMenuItem>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={handleRevoke}
            className="text-destructive focus:text-destructive"
          >
            {t("apiKeys.revoke")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
