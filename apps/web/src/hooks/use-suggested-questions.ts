/**
 * Hook TanStack Query pour les questions pré-calculées (suggested_questions)
 * agrégées cross-sources par workspace.
 * Consomme /api/v2/workspaces/:workspaceId/suggested-questions.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface SuggestedQuestion {
  question: string;
  source_id: string;
  source_name: string;
}

export function useSuggestedQuestions(workspaceId: string | undefined) {
  return useQuery<SuggestedQuestion[]>({
    queryKey: ["suggested-questions", workspaceId],
    queryFn: () =>
      api.get<SuggestedQuestion[]>(`/workspaces/${workspaceId}/suggested-questions`),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });
}
