"use client";

import { useTranslations } from "next-intl";
import { Check, X, Search } from "lucide-react";
import { toast } from "sonner";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useUpdateInsight } from "@/lib/hooks/use-insights";
import type { Insight } from "@/types/api";

interface InsightActionsProps {
  insightId: string;
  status: Insight["status"];
  workspaceId: string;
}

export function InsightActions({
  insightId,
  status,
  workspaceId,
}: InsightActionsProps) {
  const t = useTranslations("insights");
  const { mutate: update, isPending } = useUpdateInsight(workspaceId);

  function handleConfirm() {
    update({ insightId, update: { status: "confirmed" } });
  }

  function handleReject() {
    update({ insightId, update: { status: "rejected" } });
  }

  function handleInvestigate() {
    update({ insightId, update: { status: "investigating" } });
    toast.success(t("investigationLaunched"));
  }

  return (
    <div className="flex items-center gap-1">
        {status !== "confirmed" && status !== "rejected" && (
          <Tooltip>
            <TooltipTrigger
              render={
                <button
                  className="rounded-md p-1.5 text-vault-success/70 transition-colors hover:bg-vault-success/10 hover:text-vault-success disabled:opacity-40"
                  onClick={handleConfirm}
                  disabled={isPending}
                />
              }
            >
              <Check className="h-3.5 w-3.5" />
            </TooltipTrigger>
            <TooltipContent>{t("confirm")}</TooltipContent>
          </Tooltip>
        )}
        {status !== "rejected" && status !== "confirmed" && (
          <Tooltip>
            <TooltipTrigger
              render={
                <button
                  className="rounded-md p-1.5 text-destructive/70 transition-colors hover:bg-destructive/10 hover:text-destructive disabled:opacity-40"
                  onClick={handleReject}
                  disabled={isPending}
                />
              }
            >
              <X className="h-3.5 w-3.5" />
            </TooltipTrigger>
            <TooltipContent>{t("reject")}</TooltipContent>
          </Tooltip>
        )}
        {status !== "investigating" && (
          <Tooltip>
            <TooltipTrigger
              render={
                <button
                  className="rounded-md p-1.5 text-vault-accent/70 transition-colors hover:bg-vault-accent/10 hover:text-vault-accent disabled:opacity-40"
                  onClick={handleInvestigate}
                  disabled={isPending}
                />
              }
            >
              <Search className="h-3.5 w-3.5" />
            </TooltipTrigger>
            <TooltipContent>{t("investigate")}</TooltipContent>
          </Tooltip>
        )}
    </div>
  );
}
