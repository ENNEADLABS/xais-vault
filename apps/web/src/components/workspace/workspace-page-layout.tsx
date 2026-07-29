"use client";

import { useState } from "react";
import { usePanelRef } from "react-resizable-panels";
import { useMediaQuery, BREAKPOINTS } from "@/hooks/use-media-query";
import { useWorkspaceRealtime } from "@/hooks/use-workspace-realtime";
import { useSources } from "@/lib/hooks/use-sources";
import { useWorkspace } from "@/lib/hooks/use-workspace";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";
import { WorkspacePageHeader } from "./workspace-page-header";
import { SourcesPanel } from "./sources-panel";
import { ChatPanel } from "./chat-panel";
import { StudioPanel } from "./studio-panel";
import { StatusBar } from "./status-bar";
import { MobileWorkspaceLayout } from "./mobile-workspace-layout";

interface WorkspacePageLayoutProps {
  workspaceId: string;
}

export function WorkspacePageLayout({ workspaceId }: WorkspacePageLayoutProps) {
  useWorkspaceRealtime({ workspaceId });

  const isTablet = useMediaQuery(BREAKPOINTS.md);
  const isMobile = !isTablet;

  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const leftPanelRef = usePanelRef();
  const rightPanelRef = usePanelRef();

  const { data: sourcesData } = useSources(workspaceId);
  const { data: workspaceData } = useWorkspace(workspaceId);
  const sources = sourcesData?.data ?? [];
  const workspace = workspaceData?.data;

  function toggleLeft() {
    const panel = leftPanelRef.current;
    if (!panel) return;
    if (leftCollapsed) {
      panel.resize("25%");
    } else {
      panel.resize("4%");
    }
  }

  function toggleRight() {
    const panel = rightPanelRef.current;
    if (!panel) return;
    if (rightCollapsed) {
      panel.resize("35%");
    } else {
      panel.resize("4%");
    }
  }

  if (isMobile) return <MobileWorkspaceLayout workspaceId={workspaceId} />;

  return (
    <div className="flex h-screen flex-col bg-vault-bg">
      <WorkspacePageHeader workspaceId={workspaceId} />
      <div className="flex-1 min-h-0">
        <ResizablePanelGroup
          orientation="horizontal"
          className="h-full"
          resizeTargetMinimumSize={{ coarse: 20, fine: 8 }}
        >
          {/* Sources panel */}
          <ResizablePanel
            panelRef={leftPanelRef}
            defaultSize="25%"
            minSize="15%"
            maxSize="35%"
            collapsible
            collapsedSize="4%"
            onResize={(size) => setLeftCollapsed(size.asPercentage <= 5)}
          >
            <SourcesPanel
              workspaceId={workspaceId}
              collapsed={leftCollapsed}
              onCollapse={toggleLeft}
            />
          </ResizablePanel>

          <ResizableHandle className="w-px bg-vault-border hover:bg-vault-accent/50 transition-colors" />

          {/* Chat panel */}
          <ResizablePanel defaultSize="40%" minSize="25%">
            <ChatPanel workspaceId={workspaceId} />
          </ResizablePanel>

          <ResizableHandle className="w-px bg-vault-border hover:bg-vault-accent/50 transition-colors" />

          {/* Studio panel */}
          <ResizablePanel
            panelRef={rightPanelRef}
            defaultSize="35%"
            minSize="20%"
            maxSize="50%"
            collapsible
            collapsedSize="4%"
            onResize={(size) => setRightCollapsed(size.asPercentage <= 5)}
          >
            <StudioPanel
              workspaceId={workspaceId}
              collapsed={rightCollapsed}
              onToggleCollapse={toggleRight}
            />
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
      <StatusBar
        sources={sources}
        scanStatus={workspace?.scan_status ?? "pending"}
        lastUpdated={workspace?.updated_at}
      />
    </div>
  );
}
