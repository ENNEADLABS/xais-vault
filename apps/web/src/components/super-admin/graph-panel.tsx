"use client";

import {
  Building2,
  DollarSign,
  Network,
  TrendingUp,
  User,
  FileText,
  Calendar,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface GraphStats {
  total_entities: number;
  total_relations: number;
  total_chunk_links: number;
  entities_by_type: Record<string, number>;
  workspaces_with_graph: number;
  extraction_cost_total_usd: number;
  extraction_cost_24h_usd: number;
  avg_entities_per_workspace: number;
}

const TYPE_ICONS: Record<string, React.ElementType> = {
  company: Building2,
  person: User,
  metric: TrendingUp,
  clause: FileText,
  date: Calendar,
  amount: DollarSign,
};

function useGraphStats() {
  return useQuery<GraphStats>({
    queryKey: ["super-admin", "graph"],
    queryFn: () => api.get<GraphStats>("/super-admin/graph"),
    staleTime: 30_000,
  });
}

export function GraphPanel() {
  const { data, isLoading } = useGraphStats();

  if (isLoading || !data) {
    return (
      <div className="text-sm text-vault-text-muted">
        Chargement des stats graph...
      </div>
    );
  }

  if (data.total_entities === 0) {
    return (
      <div className="flex items-center justify-center py-12 font-mono text-sm text-vault-text-muted">
        Aucune donnée knowledge graph
      </div>
    );
  }

  const cards = [
    {
      label: "Entités",
      value: data.total_entities.toLocaleString(),
      badge: `${data.workspaces_with_graph} workspaces`,
      icon: Network,
    },
    {
      label: "Relations",
      value: data.total_relations.toLocaleString(),
      badge: `${data.total_chunk_links} liens chunks`,
      icon: TrendingUp,
    },
    {
      label: "Coût extraction",
      value: `$${data.extraction_cost_total_usd.toFixed(4)}`,
      badge: `$${data.extraction_cost_24h_usd.toFixed(4)} / 24h`,
      icon: DollarSign,
      alert: data.extraction_cost_24h_usd > 1.0,
    },
    {
      label: "Moy. / workspace",
      value: `${data.avg_entities_per_workspace} entités`,
      badge: "",
      icon: Building2,
    },
  ];

  return (
    <div className="space-y-4">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.label}
              className={cn(
                "rounded-lg border p-3",
                card.alert && "border-red-500/50 bg-red-500/5",
              )}
            >
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Icon className="h-3.5 w-3.5" />
                {card.label}
              </div>
              <div className="mt-1 text-lg font-semibold">{card.value}</div>
              {card.badge && (
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {card.badge}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Breakdown par type */}
      <div>
        <h4 className="mb-2 text-sm font-medium">Entités par type</h4>
        <div className="flex flex-wrap gap-2">
          {Object.entries(data.entities_by_type).map(([type, count]) => {
            const Icon = TYPE_ICONS[type] ?? FileText;
            return (
              <div
                key={type}
                className="flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs"
              >
                <Icon className="h-3 w-3" />
                <span className="font-medium">{type}</span>
                <span className="text-muted-foreground">{count}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
