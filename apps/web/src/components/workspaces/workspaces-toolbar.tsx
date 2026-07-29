"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Search, Plus } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { WorkspaceCreateDialog } from "./workspace-create-dialog";

type StatusFilter = "active" | "archived" | "closed" | null;

interface WorkspacesToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;
  status: StatusFilter;
  onStatusChange: (value: StatusFilter) => void;
}

export function WorkspacesToolbar({
  search,
  onSearchChange,
  status,
  onStatusChange,
}: WorkspacesToolbarProps) {
  const t = useTranslations("workspaces");
  const [dialogOpen, setDialogOpen] = useState(false);

  function handleStatusChange(value: string | null) {
    if (!value || value === "all") {
      onStatusChange(null);
    } else {
      onStatusChange(value as StatusFilter);
    }
  }

  return (
    <>
      <div className="flex items-center gap-3">
        {/* Titre */}
        <h1 className="text-[20px] font-semibold text-vault-text shrink-0">
          {t("title")}
        </h1>

        <div className="flex-1" />

        {/* Recherche compacte */}
        <div className="relative w-full max-w-[260px]">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-vault-text-secondary" />
          <input
            className="w-full rounded-lg border border-vault-border bg-vault-surface pl-9 pr-3 py-2 font-mono text-[13px] text-vault-text placeholder:text-vault-text-muted outline-none focus:border-vault-accent transition-colors duration-150"
            placeholder={t("searchPlaceholder")}
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>

        {/* Filtre status */}
        <Select value={status ?? "all"} onValueChange={handleStatusChange}>
          <SelectTrigger className="w-[120px] border-vault-border bg-vault-surface text-vault-text font-mono text-[12px] h-9 focus:ring-0 focus-visible:ring-0 focus:border-vault-accent transition-colors">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="border-vault-border bg-vault-surface font-mono text-[12px]">
            <SelectItem value="all">{t("filterAll")}</SelectItem>
            <SelectItem value="active">{t("filterActive")}</SelectItem>
            <SelectItem value="archived">{t("filterArchived")}</SelectItem>
            <SelectItem value="closed">{t("filterClosed")}</SelectItem>
          </SelectContent>
        </Select>

        {/* Bouton nouveau workspace */}
        <button
          type="button"
          onClick={() => setDialogOpen(true)}
          className="flex items-center gap-1.5 bg-vault-accent text-black font-mono text-[13px] uppercase tracking-wide px-4 py-2 rounded-none hover:bg-vault-accent/90 transition-colors duration-150 shrink-0"
        >
          <Plus className="h-3.5 w-3.5" />
          {t("newWorkspace")}
        </button>
      </div>

      <WorkspaceCreateDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </>
  );
}
