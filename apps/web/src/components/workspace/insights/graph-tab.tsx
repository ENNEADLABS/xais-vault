"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { Network } from "lucide-react";
import {
  useEntities,
  useEntityRelations,
  useEntityStats,
} from "@/hooks/use-entities";
import { useWorkspaceInteractionStore } from "@/stores/workspace-interaction-store";
import { GraphNodeDetail } from "./graph-node-detail";
import { GraphTypeFilters, ENTITY_TYPE_COLORS } from "./graph-type-filters";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => <GraphSkeleton />,
});

interface GraphTabProps {
  workspaceId: string;
}

interface GraphNode {
  id: string;
  name: string;
  type: string;
  val: number;
  color: string;
  mentions: number;
  description: string | null;
}

export function GraphTab({ workspaceId }: GraphTabProps) {
  const t = useTranslations("studio.graph");
  const { data: entities } = useEntities(workspaceId);
  const { data: relations } = useEntityRelations(workspaceId);
  const { data: stats } = useEntityStats(workspaceId);
  const [activeTypes, setActiveTypes] = useState<Set<string>>(new Set());
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const setPrefill = useWorkspaceInteractionStore((s) => s.setPrefillChatMessage);

  const graphData = useMemo(() => {
    if (!entities || !relations) return { nodes: [], links: [] };
    const filteredEntities =
      activeTypes.size === 0
        ? entities
        : entities.filter((e) => activeTypes.has(e.entity_type));
    const keptIds = new Set(filteredEntities.map((e) => e.id));
    return {
      nodes: filteredEntities.map((e) => ({
        id: e.id,
        name: e.name,
        type: e.entity_type,
        val: Math.max(1, Math.log(e.mention_count + 1) * 3),
        color: ENTITY_TYPE_COLORS[e.entity_type] ?? "#9ca3af",
        mentions: e.mention_count,
        description: e.description,
      })),
      links: relations
        .filter(
          (r) =>
            keptIds.has(r.source_entity_id) && keptIds.has(r.target_entity_id),
        )
        .map((r) => ({
          source: r.source_entity_id,
          target: r.target_entity_id,
          label: r.relation_type,
        })),
    };
  }, [entities, relations, activeTypes]);

  if (!stats || stats.total_entities === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <Network className="mb-2 h-10 w-10 text-vault-text-muted opacity-40" />
        <p className="text-[13px] text-vault-text">{t("emptyTitle")}</p>
        <p className="mt-1 text-[12px] text-vault-text-muted">
          {t("emptyHint")}
        </p>
      </div>
    );
  }

  return (
    <div className="relative flex h-full flex-col">
      <div className="shrink-0 border-b border-vault-border px-4 py-2">
        <div className="flex items-center justify-between gap-3">
          <div className="font-mono text-[11px] uppercase tracking-wider text-vault-text-muted">
            {t("title")} — {t("nodeCount", { count: stats.total_entities })} ·{" "}
            {t("linkCount", { count: stats.total_relations })}
          </div>
          <GraphTypeFilters
            entitiesByType={stats.entities_by_type}
            activeTypes={activeTypes}
            onToggle={(type) => {
              setActiveTypes((prev) => {
                const next = new Set(prev);
                if (next.has(type)) next.delete(type);
                else next.add(type);
                return next;
              });
            }}
          />
        </div>
      </div>
      <div
        className="relative flex-1 overflow-hidden"
        data-testid="graph-canvas"
      >
        <ForceGraph2D
          graphData={graphData}
          nodeLabel="name"
          nodeColor={(node) => (node as GraphNode).color}
          nodeVal={(node) => (node as GraphNode).val}
          linkDirectionalArrowLength={3}
          linkDirectionalArrowRelPos={1}
          linkLabel={(link) => (link as { label?: string }).label ?? ""}
          backgroundColor="transparent"
          onNodeClick={(node) => setSelectedNode(node as GraphNode)}
          cooldownTicks={80}
        />
        {selectedNode && (
          <GraphNodeDetail
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
            onAsk={(name) => {
              setPrefill(t("askAbout", { entity: name }));
              setSelectedNode(null);
            }}
          />
        )}
      </div>
    </div>
  );
}

function GraphSkeleton() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="h-32 w-32 animate-pulse rounded-full bg-vault-surface-active/40" />
    </div>
  );
}
