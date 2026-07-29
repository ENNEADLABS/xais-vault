"use client";

import { useTranslations } from "next-intl";
import { PanelRightOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useInsights } from "@/lib/hooks/use-insights";
import { useNotes } from "@/lib/hooks/use-notes";
import { ScanTab } from "./insights/scan-tab";
import { InvestigationsTab } from "./insights/investigations-tab";
import { DeliverablesTab } from "./insights/deliverables-tab";
import { NotesTab } from "./insights/notes-tab";

interface InsightsPanelProps {
  workspaceId: string;
  onCollapse?: () => void;
}

export function InsightsPanel({ workspaceId, onCollapse }: InsightsPanelProps) {
  const t = useTranslations("insights");
  const tNotes = useTranslations("notes");
  const { data: insightsData } = useInsights(workspaceId, {});
  const { data: notesData } = useNotes(workspaceId);
  const insightsCount = insightsData?.data?.length ?? 0;
  const notesCount = notesData?.data?.length ?? 0;

  return (
    <Tabs defaultValue="notes" className="flex h-full flex-col overflow-hidden">
      <div className="flex h-11 shrink-0 items-center gap-2 px-3">
        <TabsList className="self-start" variant="line">
          <TabsTrigger
            value="notes"
            className="data-active:text-vault-accent data-active:after:bg-vault-accent"
          >
            {tNotes("tabNotes")}
            {notesCount > 0 && (
              <span className="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-purple-500/15 px-1 text-[11px] font-medium text-purple-400">
                {notesCount}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="scan"
            className="data-active:text-vault-accent data-active:after:bg-vault-accent"
          >
            {t("tabScan")}
            {insightsCount > 0 && (
              <span className="ml-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-vault-accent/15 px-1 text-[11px] font-medium text-vault-accent">
                {insightsCount}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="investigations"
            className="data-active:text-vault-accent data-active:after:bg-vault-accent"
          >
            {t("tabInvestigations")}
          </TabsTrigger>
          <TabsTrigger
            value="deliverables"
            className="data-active:text-vault-accent data-active:after:bg-vault-accent"
          >
            {t("tabDeliverables")}
          </TabsTrigger>
        </TabsList>
        {onCollapse && (
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto h-7 w-7"
            onClick={onCollapse}
            aria-label={t("closePanel")}
          >
            <PanelRightOpen className="h-3.5 w-3.5 rotate-180" />
          </Button>
        )}
      </div>

      <TabsContent value="notes" className="flex-1 overflow-hidden mt-0 tab-crossfade">
        <NotesTab workspaceId={workspaceId} />
      </TabsContent>

      <TabsContent value="scan" className="flex-1 overflow-hidden mt-0 tab-crossfade">
        <ScanTab workspaceId={workspaceId} />
      </TabsContent>

      <TabsContent
        value="investigations"
        className="flex-1 overflow-hidden mt-0 tab-crossfade"
      >
        <InvestigationsTab workspaceId={workspaceId} />
      </TabsContent>

      <TabsContent value="deliverables" className="flex-1 overflow-hidden mt-0 tab-crossfade">
        <DeliverablesTab workspaceId={workspaceId} />
      </TabsContent>
    </Tabs>
  );
}
