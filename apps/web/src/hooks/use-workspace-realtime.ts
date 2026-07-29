"use client";

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRealtime } from "./use-realtime";

interface UseWorkspaceRealtimeOptions {
  workspaceId: string;
}

export function useWorkspaceRealtime({ workspaceId }: UseWorkspaceRealtimeOptions) {
  const queryClient = useQueryClient();
  const enabled = !!workspaceId;

  // Sources : processing → ready/failed
  const invalidateSources = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["sources", workspaceId] });
  }, [queryClient, workspaceId]);

  useRealtime({
    table: "sources",
    filter: `workspace_id=eq.${workspaceId}`,
    events: ["UPDATE"],
    onEvent: invalidateSources,
    enabled,
  });

  // Workspace : scan_status change (scanning → scanned/failed)
  const invalidateWorkspace = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["workspace", workspaceId] });
    // Quand le scan est terminé, les insights sont aussi prêts
    void queryClient.invalidateQueries({ queryKey: ["insights", workspaceId] });
  }, [queryClient, workspaceId]);

  useRealtime({
    table: "workspaces",
    filter: `id=eq.${workspaceId}`,
    events: ["UPDATE"],
    onEvent: invalidateWorkspace,
    enabled,
  });

  // Insights : INSERT (nouveaux insights) ou UPDATE (status change)
  const invalidateInsights = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["insights", workspaceId] });
  }, [queryClient, workspaceId]);

  useRealtime({
    table: "insights",
    filter: `workspace_id=eq.${workspaceId}`,
    events: ["INSERT", "UPDATE"],
    onEvent: invalidateInsights,
    enabled,
  });

  // Investigations : status change (processing → completed/failed)
  const invalidateInvestigations = useCallback(() => {
    void queryClient.invalidateQueries({
      queryKey: ["investigations", workspaceId],
    });
  }, [queryClient, workspaceId]);

  useRealtime({
    table: "investigations",
    filter: `workspace_id=eq.${workspaceId}`,
    events: ["INSERT", "UPDATE"],
    onEvent: invalidateInvestigations,
    enabled,
  });

  // Deliverables : status change (processing → completed/failed)
  const invalidateDeliverables = useCallback(() => {
    void queryClient.invalidateQueries({
      queryKey: ["deliverables", workspaceId],
    });
  }, [queryClient, workspaceId]);

  useRealtime({
    table: "deliverables",
    filter: `workspace_id=eq.${workspaceId}`,
    events: ["INSERT", "UPDATE"],
    onEvent: invalidateDeliverables,
    enabled,
  });
}
