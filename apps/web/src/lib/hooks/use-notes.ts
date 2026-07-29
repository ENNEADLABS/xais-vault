"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type ApiResponse } from "@/lib/api";
import type { Note, ChecklistItem } from "@/types/api";

export function useNotes(workspaceId: string) {
  return useQuery({
    queryKey: ["notes", workspaceId],
    queryFn: () => api.get<ApiResponse<Note[]>>(`/workspaces/${workspaceId}/notes/`),
    enabled: !!workspaceId,
  });
}

export function useCreateNote(workspaceId: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      content: string;
      title?: string;
      tags?: string[];
      is_pinned?: boolean;
      checklist_items?: ChecklistItem[];
      linked_source_id?: string;
      linked_insight_id?: string;
      linked_message_id?: string;
    }) => api.post<ApiResponse<Note>>(`/workspaces/${workspaceId}/notes/`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["notes", workspaceId] });
    },
  });
}

export function useUpdateNote(workspaceId: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({
      noteId,
      update,
    }: {
      noteId: string;
      update: Partial<
        Omit<Note, "id" | "workspace_id" | "user_id" | "created_at" | "updated_at">
      >;
    }) =>
      api.patch<ApiResponse<Note>>(`/workspaces/${workspaceId}/notes/${noteId}`, update),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["notes", workspaceId] });
    },
  });
}

export function useDeleteNote(workspaceId: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (noteId: string) =>
      api.delete(`/workspaces/${workspaceId}/notes/${noteId}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["notes", workspaceId] });
    },
  });
}
