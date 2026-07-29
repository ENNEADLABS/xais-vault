"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { Link } from "@/i18n/navigation";
import { FileText, AlertTriangle, MoreVertical, Pencil, Trash2 } from "lucide-react";
import { cn, formatRelativeDate } from "@/lib/utils";
import { useUpdateWorkspace, useDeleteWorkspace } from "@/lib/hooks/use-workspaces";
import type { Workspace } from "@/types/api";
import { WorkspaceIcon } from "./workspace-icon";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface WorkspaceCardProps {
  workspace: Workspace;
}

// border-l-2 colorée par status (border-l-* + border-l-[color])
const STATUS_BORDER_L: Record<string, string> = {
  active: "border-l-vault-accent",
  archived: "border-l-vault-text-muted",
  closed: "border-l-vault-danger",
};

const SCAN_CLASSES: Record<string, string> = {
  pending: "bg-vault-warning-dim text-vault-warning",
  scanning: "bg-vault-accent-dim text-vault-accent animate-[vault-pulse_1.5s_ease-in-out_infinite]",
  completed: "bg-vault-success-dim text-vault-success",
  failed: "bg-vault-danger-dim text-vault-danger",
};

const SCAN_TAG: Record<string, string> = {
  pending: "[PENDING]",
  scanning: "[SCANNING]",
  completed: "[DONE]",
  failed: "[FAILED]",
};

export function WorkspaceCard({ workspace }: WorkspaceCardProps) {
  const t = useTranslations("workspaces");
  const locale = useLocale();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [newName, setNewName] = useState(workspace.name);

  const { mutateAsync: updateWorkspace, isPending: isRenaming } = useUpdateWorkspace();
  const { mutateAsync: deleteWorkspace, isPending: isDeleting } = useDeleteWorkspace();

  const scanLabel: Record<string, string> = {
    pending: t("scanPending"),
    scanning: t("scanScanning"),
    completed: t("scanCompleted"),
    failed: t("scanFailed"),
  };

  const borderL = STATUS_BORDER_L[workspace.status] ?? "border-l-zinc-600";
  const scanClass = SCAN_CLASSES[workspace.scan_status] ?? SCAN_CLASSES.pending;
  const scanTag = SCAN_TAG[workspace.scan_status] ?? `[${workspace.scan_status.toUpperCase()}]`;

  async function handleRename() {
    if (!newName.trim() || newName === workspace.name) {
      setRenameOpen(false);
      return;
    }
    await updateWorkspace({ workspaceId: workspace.id, name: newName.trim() });
    setRenameOpen(false);
  }

  async function handleDelete() {
    await deleteWorkspace(workspace.id);
    setDeleteOpen(false);
  }

  return (
    <>
      <div
        className={cn(
          "vault-card group relative flex cursor-pointer flex-col overflow-hidden",
          "border border-vault-border border-l-2 bg-vault-surface rounded-lg",
          "transition-all duration-200",
          "hover:-translate-y-1 hover:border-vault-border-active hover:shadow-vault-hover",
          borderL,
        )}
      >
        {/* Header */}
        <Link
          href={`/workspaces/${workspace.id}`}
          className="pl-4 pr-3 pt-3 pb-2 focus-visible:outline-2 focus-visible:outline-vault-accent focus-visible:outline-offset-2"
        >
          <div className="flex items-start gap-2.5">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center text-lg leading-none">
              <WorkspaceIcon emoji={workspace.emoji} className="h-4 w-4 text-vault-text-muted" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold text-base text-vault-text leading-tight">
                {workspace.name}
              </p>
              {workspace.target_company && (
                <p className="truncate font-mono text-[11px] text-vault-text-secondary mt-0.5">
                  {workspace.target_company}
                </p>
              )}
            </div>
            {/* Scan status tag */}
            <span
              className={cn(
                "shrink-0 font-mono text-[11px] font-medium px-1.5 py-0.5 tracking-tight",
                scanClass,
              )}
              title={scanLabel[workspace.scan_status] ?? workspace.scan_status}
            >
              {scanTag}
            </span>
          </div>
        </Link>

        {/* Menu trois points — visible au hover */}
        <div className="absolute top-2.5 right-2 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
          <DropdownMenu>
            <DropdownMenuTrigger
              className="h-7 w-7 flex items-center justify-center rounded hover:bg-vault-surface-hover text-vault-text-muted hover:text-vault-text transition-colors"
              onClick={(e) => e.preventDefault()}
            >
              <MoreVertical className="h-4 w-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
              <DropdownMenuItem
                onClick={(e) => { e.preventDefault(); setRenameOpen(true); }}
              >
                <Pencil className="h-3.5 w-3.5 mr-2" />
                {t("rename")}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={(e) => { e.preventDefault(); setDeleteOpen(true); }}
                className="text-vault-danger focus:text-vault-danger"
              >
                <Trash2 className="h-3.5 w-3.5 mr-2" />
                {t("delete")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Status badge — uniquement pour archived/closed (active est implicite) */}
        {workspace.status !== "active" && (
          <div className="pl-4 pr-3 pb-2.5">
            <span
              className={cn(
                "inline-block font-mono text-[11px] tracking-wider uppercase px-1.5 py-0.5",
                workspace.status === "archived" && "bg-vault-text-muted/10 text-vault-text-muted",
                workspace.status === "closed" && "bg-vault-danger/10 text-vault-danger",
              )}
            >
              {workspace.status === "archived" ? t("statusArchived") : t("statusClosed")}
            </span>
          </div>
        )}

        {/* Footer */}
        <Link
          href={`/workspaces/${workspace.id}`}
          className="mt-auto flex justify-between border-t border-vault-border bg-vault-surface-active px-4 py-2 font-mono text-[11px] text-vault-text-secondary"
        >
          <span className="flex items-center gap-1">
            <FileText className="h-3 w-3 shrink-0" />
            {t("sources", { count: workspace.source_count })}
          </span>
          <span className="flex items-center gap-1">
            <AlertTriangle className="h-3 w-3 shrink-0" />
            {t("insights", { count: workspace.insight_count })}
          </span>
          <span className="tabular-nums">
            {formatRelativeDate(workspace.updated_at, locale)}
          </span>
        </Link>
      </div>

      {/* Dialog renommer */}
      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent className="max-w-sm bg-vault-surface">
          <DialogHeader>
            <DialogTitle className="font-mono text-[14px] uppercase tracking-wider">
              {t("rename")}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => { e.preventDefault(); void handleRename(); }}
            className="space-y-4"
          >
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={t("renamePlaceholder")}
              className="w-full rounded-lg border border-vault-border bg-vault-surface px-3 py-2 text-[13px] text-vault-text focus:border-vault-accent focus:outline-none"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" type="button" onClick={() => setRenameOpen(false)}>
                {t("cancel")}
              </Button>
              <Button
                type="submit"
                disabled={isRenaming || !newName.trim()}
                className="bg-vault-accent text-black hover:bg-vault-accent/90"
              >
                {t("renameSubmit")}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Dialog confirmation suppression */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteConfirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteConfirmDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => void handleDelete()}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t("deleteConfirmButton")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
