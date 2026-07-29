/**
 * Hook TanStack Query pour le knowledge graph (entités + relations).
 * Consomme /api/v2/workspaces/:workspaceId/entities.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ─── Types ───────────────────────────────────────────────────

interface Entity {
  id: string;
  workspace_id: string;
  name: string;
  entity_type: string;
  description: string | null;
  properties: Record<string, unknown>;
  mention_count: number;
  created_at: string;
}

interface EntityRelation {
  id: string;
  source_entity_id: string;
  source_entity_name: string;
  target_entity_id: string;
  target_entity_name: string;
  relation_type: string;
  description: string | null;
  confidence: number;
  created_at: string;
}

interface EntityStats {
  total_entities: number;
  total_relations: number;
  entities_by_type: Record<string, number>;
}

// ─── Hooks ────────────────────────────────────��──────────────

export function useEntities(workspaceId: string | undefined, entityType?: string) {
  const params = entityType ? `?entity_type=${entityType}` : "";
  return useQuery<Entity[]>({
    queryKey: ["entities", workspaceId, entityType],
    queryFn: () => api.get<Entity[]>(`/workspaces/${workspaceId}/entities${params}`),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });
}

export function useEntityRelations(workspaceId: string | undefined) {
  return useQuery<EntityRelation[]>({
    queryKey: ["entity-relations", workspaceId],
    queryFn: () =>
      api.get<EntityRelation[]>(`/workspaces/${workspaceId}/entities/relations`),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });
}

export function useEntityStats(workspaceId: string | undefined) {
  return useQuery<EntityStats>({
    queryKey: ["entity-stats", workspaceId],
    queryFn: () => api.get<EntityStats>(`/workspaces/${workspaceId}/entities/stats`),
    enabled: !!workspaceId,
    staleTime: 60_000,
  });
}

export type { Entity, EntityRelation, EntityStats };
