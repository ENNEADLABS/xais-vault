"use client";

import { useTranslations } from "next-intl";
import { ArrowLeft, Settings, Loader2 } from "lucide-react";
import { WorkspaceIcon } from "@/components/workspaces/workspace-icon";
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { useWorkspace } from "@/lib/hooks/use-workspace";
import { cn } from "@/lib/utils";

const SCAN_CLASSES: Record<string, string> = {
  pending: "bg-vault-warning/10 text-vault-warning/80 border border-vault-warning/20",
  scanning: "bg-vault-accent/10 text-vault-accent/80 border border-vault-accent/20 animate-[vault-pulse_1.5s_ease-in-out_infinite]",
  scanned: "bg-vault-success/10 text-vault-success/80 border border-vault-success/20",
  failed: "bg-vault-danger/10 text-vault-danger/80 border border-vault-danger/20",
};

interface WorkspacePageHeaderProps {
  workspaceId: string;
}

export function WorkspacePageHeader({ workspaceId }: WorkspacePageHeaderProps) {
  const t = useTranslations("workspace_page");
  const { data, isLoading, isError } = useWorkspace(workspaceId);
  const workspace = data?.data;

  const scanLabel: Record<string, string> = {
    pending: t("statusPending"),
    scanning: t("statusProcessing"),
    scanned: t("statusReady"),
    failed: t("statusFailed"),
  };

  return (
    <div className="flex h-13 shrink-0 items-center gap-2 border-b border-vault-border bg-vault-surface px-4 shadow-vault-sm">
      <Link href="/workspaces">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          title={t("backToWorkspaces")}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
      </Link>
      {isLoading ? (
        <>
          <Skeleton className="h-8 w-8 rounded" />
          <Skeleton className="h-5 w-40" />
        </>
      ) : isError ? (
        <span className="font-mono text-[12px] text-vault-danger uppercase tracking-wide">
          LOAD_FAILED
        </span>
      ) : workspace ? (
        <>
          <span className="flex h-7 w-7 shrink-0 items-center justify-center text-lg leading-none">
            <WorkspaceIcon emoji={workspace.emoji} className="h-4 w-4 text-vault-text-muted" />
          </span>
          <p className="truncate font-semibold">{workspace.name}</p>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded px-2.5 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wide",
              SCAN_CLASSES[workspace.scan_status] ?? SCAN_CLASSES.pending,
            )}
          >
            {workspace.scan_status === "scanning" && (
              <Loader2 className="h-3 w-3 animate-spin" />
            )}
            {scanLabel[workspace.scan_status] ?? workspace.scan_status}
          </span>
        </>
      ) : null}

      {workspace && (
        <div className="ml-2 flex items-center gap-2 text-vault-text-muted text-[12px]">
          <span>{t("headerSources", { count: workspace.source_count })}</span>
          <span className="text-vault-border">|</span>
          <span>{t("headerInsights", { count: workspace.insight_count })}</span>
        </div>
      )}

      <div className="ml-auto flex items-center gap-1">
        <ThemeToggle />
        <Link href="/settings">
          <Button variant="ghost" size="icon" title={t("settings")}>
            <Settings className="h-4 w-4" />
          </Button>
        </Link>
      </div>
    </div>
  );
}
