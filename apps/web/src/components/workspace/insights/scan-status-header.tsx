"use client";

import { useTranslations } from "next-intl";
import { Clock, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { useWorkspace } from "@/lib/hooks/use-workspace";
import type { Workspace } from "@/types/api";

const STATUS_CONFIG: Record<
  Workspace["scan_status"],
  {
    icon: React.ElementType;
    labelKey: string;
    className: string;
    iconClassName?: string;
  }
> = {
  pending: {
    icon: Clock,
    labelKey: "scanPending",
    className: "text-muted-foreground",
  },
  scanning: {
    icon: Loader2,
    labelKey: "scanScanning",
    className: "text-vault-accent animate-pulse",
    iconClassName: "animate-spin",
  },
  scanned: {
    icon: CheckCircle,
    labelKey: "scanCompleted",
    className: "text-vault-success",
  },
  failed: {
    icon: AlertCircle,
    labelKey: "scanFailed",
    className: "text-vault-danger",
  },
};

interface ScanStatusHeaderProps {
  workspaceId: string;
  insightsCount?: number;
}

export function ScanStatusHeader({
  workspaceId,
  insightsCount,
}: ScanStatusHeaderProps) {
  const t = useTranslations("insights");
  const { data } = useWorkspace(workspaceId);
  const workspace = data?.data;

  if (!workspace) return null;

  const config = STATUS_CONFIG[workspace.scan_status];
  const Icon = config.icon;

  const label =
    workspace.scan_status === "scanned" && insightsCount !== undefined
      ? t("insightsCount", { count: insightsCount })
      : t(config.labelKey as Parameters<typeof t>[0]);

  return (
    <>
      <div
        className={cn(
          "flex items-center gap-2 border-b px-3 py-2 text-xs font-medium",
          config.className,
        )}
      >
        <Icon className={cn("h-3.5 w-3.5 shrink-0", config.iconClassName)} />
        <span>{label}</span>
      </div>

      {workspace.scan_status === "scanning" && (
        <div className="h-0.5 w-full overflow-hidden bg-vault-surface">
          <div className="h-full w-1/2 animate-progress rounded-full bg-vault-accent" />
        </div>
      )}
    </>
  );
}
