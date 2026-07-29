"use client";

import { useTranslations } from "next-intl";
import { TerminalField } from "@/components/ui/terminal-field";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const DEAL_TYPES = ["equity", "debt", "ma", "restructuring", "other"] as const;

interface WorkspaceFormFieldsProps {
  workspaceType: string;
  onWorkspaceTypeChange: (v: string) => void;
  sector: string;
  onSectorChange: (v: string) => void;
}

export function WorkspaceFormFields({
  workspaceType,
  onWorkspaceTypeChange,
  sector,
  onSectorChange,
}: WorkspaceFormFieldsProps) {
  const t = useTranslations("workspaces.create");

  const workspaceTypeKeys: Record<string, string> = {
    equity: t("workspaceTypeEquity"),
    debt: t("workspaceTypeDebt"),
    ma: t("workspaceTypeMa"),
    restructuring: t("workspaceTypeRestructuring"),
    other: t("workspaceTypeOther"),
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-1.5">
        <p className="font-mono text-[12px] uppercase tracking-wider text-vault-text-secondary mb-1.5">
          {t("workspaceTypeLabel")}
        </p>
        <Select
          value={workspaceType}
          onValueChange={(v) => onWorkspaceTypeChange(v ?? "")}
        >
          <SelectTrigger className="rounded-none border-0 border-b border-vault-border bg-transparent h-10 px-0 font-mono text-[13px] text-vault-text focus:ring-0 focus-visible:ring-0 data-[state=open]:border-vault-accent transition-colors duration-150">
            <SelectValue placeholder={t("workspaceTypePlaceholder")} />
          </SelectTrigger>
          <SelectContent>
            {DEAL_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {workspaceTypeKeys[type]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <TerminalField
        id="sector"
        label={t("sectorLabel")}
        placeholder={t("sectorPlaceholder")}
        value={sector}
        onChange={(e) => onSectorChange(e.target.value)}
      />
    </div>
  );
}
