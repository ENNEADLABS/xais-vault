import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { ScanTab } from "./scan-tab";
import type { Insight } from "@/types/api";

// ─── Mocks ───────────────────────────────────────────────

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

function makeInsight(overrides: Partial<Insight> = {}): Insight {
  return {
    id: "f-1",
    workspace_id: "workspace-1",
    organization_id: "org-1",
    type: "red_flag",
    severity: "medium",
    confidence_score: 70,
    title: "Test insight",
    description: "Description",
    source_id: null,
    source_name: null,
    source_page: null,
    source_section: null,
    source_quote: null,
    status: "pending",
    reviewed_by: null,
    reviewed_at: null,
    verification: null,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
    ...overrides,
  };
}

const FINDINGS: Insight[] = [
  makeInsight({ id: "f-1", title: "Low conf", severity: "low", confidence_score: 30, created_at: "2025-01-01T00:00:00Z" }),
  makeInsight({ id: "f-2", title: "Critical issue", severity: "critical", confidence_score: 90, created_at: "2025-01-03T00:00:00Z" }),
  makeInsight({ id: "f-3", title: "Medium alert", severity: "medium", confidence_score: 60, created_at: "2025-01-02T00:00:00Z" }),
];

const mockUseInsights = vi.fn();

vi.mock("@/lib/hooks/use-insights", () => ({
  useInsights: (...args: unknown[]) => mockUseInsights(...args),
}));

// Mock les sous-composants qui utilisent des hooks/i18n complexes
vi.mock("./scan-status-header", () => ({
  ScanStatusHeader: ({ insightsCount }: { insightsCount: number }) => (
    <div data-testid="status-header">Insights: {insightsCount}</div>
  ),
}));

vi.mock("./insight-card", () => ({
  InsightCard: ({ insight }: { insight: Insight }) => (
    <div data-testid={`insight-${insight.id}`}>{insight.title}</div>
  ),
}));

vi.mock("./insight-card-skeleton", () => ({
  InsightCardSkeleton: () => <div data-testid="skeleton" />,
}));

vi.mock("@/lib/hooks/use-insights", async () => ({
  useInsights: (...args: unknown[]) => mockUseInsights(...args),
}));

vi.mock("@/components/ui/empty-state", () => ({
  EmptyState: () => <div data-testid="empty-state" />,
}));

describe("ScanTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseInsights.mockReturnValue({
      data: { data: FINDINGS },
      isLoading: false,
    });
  });

  it("renders severity counters when insights exist", () => {
    renderWithProviders(<ScanTab workspaceId="workspace-1" />);
    // SeverityCounters affiche les labels
    expect(screen.getByText("1 Critical")).toBeInTheDocument();
    expect(screen.getByText("1 Medium")).toBeInTheDocument();
    expect(screen.getByText("1 Low")).toBeInTheDocument();
  });

  it("renders insights count in header", () => {
    renderWithProviders(<ScanTab workspaceId="workspace-1" />);
    expect(screen.getByText("Insights: 3")).toBeInTheDocument();
  });

  it("shows skeletons when loading", () => {
    mockUseInsights.mockReturnValue({ data: undefined, isLoading: true });
    renderWithProviders(<ScanTab workspaceId="workspace-1" />);
    expect(screen.getAllByTestId("skeleton")).toHaveLength(3);
  });

  it("shows empty state when no insights", () => {
    mockUseInsights.mockReturnValue({ data: { data: [] }, isLoading: false });
    renderWithProviders(<ScanTab workspaceId="workspace-1" />);
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
  });

  it("sorts by severity by default (critical first)", () => {
    renderWithProviders(<ScanTab workspaceId="workspace-1" />);
    const cards = screen.getAllByTestId(/^insight-/);
    // Default sort: severity → critical, medium, low
    expect(cards[0]).toHaveTextContent("Critical issue");
    expect(cards[1]).toHaveTextContent("Medium alert");
    expect(cards[2]).toHaveTextContent("Low conf");
  });

  it("sorts by confidence when selected", () => {
    renderWithProviders(<ScanTab workspaceId="workspace-1" />);

    const sortSelect = screen.getByDisplayValue("sortSeverity");
    fireEvent.change(sortSelect, { target: { value: "confidence" } });

    const cards = screen.getAllByTestId(/^insight-/);
    // Sort by confidence desc: 90, 60, 30
    expect(cards[0]).toHaveTextContent("Critical issue");
    expect(cards[1]).toHaveTextContent("Medium alert");
    expect(cards[2]).toHaveTextContent("Low conf");
  });

  it("sorts by date when selected", () => {
    renderWithProviders(<ScanTab workspaceId="workspace-1" />);

    const sortSelect = screen.getByDisplayValue("sortSeverity");
    fireEvent.change(sortSelect, { target: { value: "date" } });

    const cards = screen.getAllByTestId(/^insight-/);
    // Sort by date desc: Jan 3 (f-2), Jan 2 (f-3), Jan 1 (f-1)
    expect(cards[0]).toHaveTextContent("Critical issue");
    expect(cards[1]).toHaveTextContent("Medium alert");
    expect(cards[2]).toHaveTextContent("Low conf");
  });

  it("has sort select with 4 options", () => {
    renderWithProviders(<ScanTab workspaceId="workspace-1" />);
    const sortSelect = screen.getByDisplayValue("sortSeverity");
    const options = sortSelect.querySelectorAll("option");
    expect(options).toHaveLength(4);
  });
});
