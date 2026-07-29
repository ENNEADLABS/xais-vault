"use client";

import { useTranslations } from "next-intl";
import { Microscope } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { useInvestigations } from "@/lib/hooks/use-investigations";
import { InvestigationCard } from "./investigation-card";
import { InvestigationCardSkeleton } from "./investigation-card-skeleton";

interface InvestigationsTabProps {
  workspaceId: string;
}

export function InvestigationsTab({ workspaceId }: InvestigationsTabProps) {
  const t = useTranslations("investigations");
  const { data, isLoading } = useInvestigations(workspaceId);
  const investigations = data?.data ?? [];

  return (
    <div className="flex h-full flex-col overflow-y-auto p-2">
      {isLoading ? (
        <div className="space-y-3">
          <InvestigationCardSkeleton />
          <InvestigationCardSkeleton />
        </div>
      ) : investigations.length === 0 ? (
        <EmptyState
          icon={Microscope}
          title={t("noInvestigations")}
          description={t("noInvestigationsHint")}
          label="NO_INVESTIGATIONS"
        />
      ) : (
        <div className="space-y-3">
          {investigations.map((inv) => (
            <InvestigationCard key={inv.id} investigation={inv} />
          ))}
        </div>
      )}
    </div>
  );
}
