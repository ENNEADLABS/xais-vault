"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

type ScanMode = "quick" | "standard" | "deep";

export function useLaunchScan(workspaceId: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (mode: ScanMode = "standard") =>
      api.post(`/workspaces/${workspaceId}/scan`, { mode }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["workspace", workspaceId] });
      void qc.invalidateQueries({ queryKey: ["insights", workspaceId] });
    },
  });
}
