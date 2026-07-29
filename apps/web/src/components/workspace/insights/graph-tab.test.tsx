/**
 * Tests minimum pour GraphTab.
 * Le canvas ForceGraph2D (next/dynamic) n'est pas rendu en jsdom sans canvas setup.
 * Le mock global de next-intl (src/test/setup.ts) retourne les clés i18n telles
 * quelles, donc les assertions ciblent les clés de traduction.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { GraphTab } from "./graph-tab";
import { mockQuerySuccess } from "@/tests/mocks/query-result";
import type { Entity, EntityRelation, EntityStats } from "@/hooks/use-entities";

vi.mock("next/dynamic", () => ({
  default: () => {
    const Mock = () => <div data-testid="force-graph-mock" />;
    Mock.displayName = "ForceGraph2DMock";
    return Mock;
  },
}));

vi.mock("@/hooks/use-entities", () => ({
  useEntities: vi.fn(),
  useEntityRelations: vi.fn(),
  useEntityStats: vi.fn(),
}));

vi.mock("@/stores/workspace-interaction-store", () => ({
  useWorkspaceInteractionStore: (
    selector: (s: {
      setPrefillChatMessage: (msg: string | null) => void;
    }) => unknown,
  ) => selector({ setPrefillChatMessage: vi.fn() }),
}));

import {
  useEntities,
  useEntityRelations,
  useEntityStats,
} from "@/hooks/use-entities";

describe("GraphTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("devrait afficher l'empty state quand aucune entité n'existe", () => {
    vi.mocked(useEntityStats).mockReturnValue(
      mockQuerySuccess<EntityStats>({
        total_entities: 0,
        total_relations: 0,
        entities_by_type: {},
      }),
    );
    vi.mocked(useEntities).mockReturnValue(mockQuerySuccess<Entity[]>([]));
    vi.mocked(useEntityRelations).mockReturnValue(
      mockQuerySuccess<EntityRelation[]>([]),
    );

    render(<GraphTab workspaceId="workspace-1" />);

    expect(screen.getByText("emptyTitle")).toBeInTheDocument();
    expect(screen.getByText("emptyHint")).toBeInTheDocument();
  });

  it("devrait rendre le container du graphe quand des entités existent", () => {
    vi.mocked(useEntityStats).mockReturnValue(
      mockQuerySuccess<EntityStats>({
        total_entities: 12,
        total_relations: 5,
        entities_by_type: { company: 7, person: 5 },
      }),
    );
    vi.mocked(useEntities).mockReturnValue(
      mockQuerySuccess<Entity[]>([
        {
          id: "e1",
          workspace_id: "workspace-1",
          name: "Acme Corp",
          entity_type: "company",
          description: null,
          properties: {},
          mention_count: 5,
          created_at: "2026-04-20",
        },
      ]),
    );
    vi.mocked(useEntityRelations).mockReturnValue(
      mockQuerySuccess<EntityRelation[]>([]),
    );

    render(<GraphTab workspaceId="workspace-1" />);

    expect(screen.getByTestId("graph-canvas")).toBeInTheDocument();
    expect(screen.queryByText("emptyTitle")).not.toBeInTheDocument();
  });
});
