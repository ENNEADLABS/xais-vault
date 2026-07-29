"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Plus, FileOutput } from "lucide-react";
import { useWorkspace } from "@/lib/hooks/use-workspace";
import { useDeliverables } from "@/lib/hooks/use-deliverables";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { DeliverableCard } from "./deliverable-card";
import { DeliverableCardSkeleton } from "./deliverable-card-skeleton";
import { GenerateDeliverableDialog } from "./generate-deliverable-dialog";

interface DeliverablesTabProps {
  workspaceId: string;
}

export function DeliverablesTab({ workspaceId }: DeliverablesTabProps) {
  const t = useTranslations("deliverables");
  const [dialogOpen, setDialogOpen] = useState(false);
  const { data: workspaceData } = useWorkspace(workspaceId);
  const { data, isLoading } = useDeliverables(workspaceId);
  const deliverables = data?.data ?? [];
  const workspaceName = workspaceData?.data?.name ?? "";

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between border-b px-3 py-2">
        <span className="text-sm font-medium">{t("title")}</span>
        <Button variant="ghost" size="sm" onClick={() => setDialogOpen(true)}>
          <Plus className="h-3.5 w-3.5 mr-1" />
          {t("generate")}
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {isLoading ? (
          <>
            <DeliverableCardSkeleton />
            <DeliverableCardSkeleton />
          </>
        ) : deliverables.length === 0 ? (
          <EmptyState
            icon={FileOutput}
            title={t("noDeliverables")}
            description={t("noDeliverablesHint")}
            label="NO_DELIVERABLES"
            action={{
              label: t("generate"),
              onClick: () => setDialogOpen(true),
            }}
          />
        ) : (
          deliverables.map((del) => (
            <DeliverableCard key={del.id} deliverable={del} />
          ))
        )}
      </div>

      <GenerateDeliverableDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        workspaceId={workspaceId}
        dealName={workspaceName}
      />
    </div>
  );
}
