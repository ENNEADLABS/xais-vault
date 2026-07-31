import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { InsightCard } from "./insight-card";
import type { Insight } from "@/types/api";

const mockMutate = vi.fn();

vi.mock("@/lib/hooks/use-insights", () => ({
  useUpdateInsight: vi.fn(() => ({
    mutate: mockMutate,
    isPending: false,
  })),
  useInsights: vi.fn(() => ({ data: { data: [] } })),
}));

vi.mock("@/lib/hooks/use-notes", () => ({
  useNotes: vi.fn(() => ({ data: { data: [] } })),
  useCreateNote: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useUpdateNote: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("@/lib/hooks/use-sources", () => ({
  useSources: vi.fn(() => ({ data: { data: [] } })),
}));

vi.mock("@/lib/hooks/use-investigations", () => ({
  useCreateInvestigation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

const FINDING: Insight = {
  id: "f-1",
  workspace_id: "workspace-1",
  organization_id: "org-1",
  type: "red_flag",
  severity: "high",
  confidence_score: 85,
  title: "Valorisation incohérente",
  description: "Ecart de 20% entre memo et term sheet",
  source_id: "src-1",
  source_name: "Investment Memo.pdf",
  source_page: 3,
  source_section: "Valorisation",
  source_quote: "Valorisation pré-money : 50M€",
  status: "pending",
  reviewed_by: null,
  reviewed_at: null,
  verification: null,
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
};

describe("InsightCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title", () => {
    renderWithProviders(<InsightCard insight={FINDING} workspaceId="workspace-1" />);
    expect(screen.getByText("Valorisation incohérente")).toBeInTheDocument();
  });

  it("renders description", () => {
    renderWithProviders(<InsightCard insight={FINDING} workspaceId="workspace-1" />);
    expect(
      screen.getByText("Ecart de 20% entre memo et term sheet"),
    ).toBeInTheDocument();
  });

  it("renders status badge", () => {
    renderWithProviders(<InsightCard insight={FINDING} workspaceId="workspace-1" />);
    expect(screen.getByText("statusPending")).toBeInTheDocument();
  });

  it("renders severity badge", () => {
    renderWithProviders(<InsightCard insight={FINDING} workspaceId="workspace-1" />);
    expect(screen.getByText("severityHigh")).toBeInTheDocument();
  });

  it("renders confidence score", () => {
    renderWithProviders(<InsightCard insight={FINDING} workspaceId="workspace-1" />);
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("renders source quote", () => {
    renderWithProviders(<InsightCard insight={FINDING} workspaceId="workspace-1" />);
    expect(screen.getByText(/Valorisation pré-money/)).toBeInTheDocument();
  });

  it("card is clickable with role button", () => {
    renderWithProviders(<InsightCard insight={FINDING} workspaceId="workspace-1" />);
    const cards = screen.getAllByRole("button");
    // Le card lui-même + les 3 boutons d'action (confirm/reject/investigate)
    expect(cards.length).toBeGreaterThanOrEqual(1);
  });

  it("hides action buttons when not pending", () => {
    const confirmed = { ...FINDING, status: "confirmed" as const };
    renderWithProviders(<InsightCard insight={confirmed} workspaceId="workspace-1" />);
    // Seul le card a role=button, pas les actions
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(1);
  });
});
