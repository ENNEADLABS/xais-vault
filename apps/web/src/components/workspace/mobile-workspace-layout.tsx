"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FileText, MessageSquare, ListChecks } from "lucide-react";
import { WorkspacePageHeader } from "./workspace-page-header";
import { SourcesPanel } from "./sources-panel";
import { ChatPanel } from "./chat-panel";
import { InsightsPanel } from "./insights-panel";

type MobileTab = "sources" | "chat" | "insights";

interface MobileWorkspaceLayoutProps {
  workspaceId: string;
}

const TAB_ICONS = {
  sources: FileText,
  chat: MessageSquare,
  insights: ListChecks,
} as const;

const TAB_KEYS: MobileTab[] = ["sources", "chat", "insights"];

export function MobileWorkspaceLayout({ workspaceId }: MobileWorkspaceLayoutProps) {
  const t = useTranslations("workspace_page.mobileTabs");
  const [mobileTab, setMobileTab] = useState<MobileTab>("chat");

  return (
    <div className="flex h-screen flex-col bg-background">
      <WorkspacePageHeader workspaceId={workspaceId} />
      <div className="flex-1 overflow-hidden">
        {mobileTab === "sources" && <SourcesPanel workspaceId={workspaceId} />}
        {mobileTab === "chat" && <ChatPanel workspaceId={workspaceId} />}
        {mobileTab === "insights" && <InsightsPanel workspaceId={workspaceId} />}
      </div>
      <nav className="flex h-12 shrink-0 items-center border-t border-vault-border bg-vault-surface pb-[env(safe-area-inset-bottom)]">
        {TAB_KEYS.map((key) => {
          const Icon = TAB_ICONS[key];
          return (
            <button
              key={key}
              onClick={() => setMobileTab(key)}
              className={`flex flex-1 flex-col items-center justify-center gap-0.5 py-1.5 text-[11px] font-medium transition-colors ${
                mobileTab === key
                  ? "text-vault-accent"
                  : "text-vault-text-muted hover:text-vault-text"
              }`}
            >
              <Icon className="h-4 w-4" />
              {t(key)}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
