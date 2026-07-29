import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { RiskMatrix } from "./risk-matrix";
import type { Insight } from "@/types/api";

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

function makeInsight(overrides: Partial<Insight> = {}): Insight {
  return {
    id: "f-1",
    workspace_id: "workspace-1",
    organization_id: "org-1",
    type: "red_flag",
    severity: "high",
    confidence_score: 75,
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

describe("RiskMatrix", () => {
  const mockOnClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders SVG with aria-label", () => {
    renderWithProviders(<RiskMatrix insights={[]} />);
    expect(
      screen.getByRole("img", { name: /Risk Matrix/ }),
    ).toBeInTheDocument();
  });

  it("renders severity axis labels", () => {
    renderWithProviders(<RiskMatrix insights={[]} />);
    expect(screen.getByText("Critique")).toBeInTheDocument();
    expect(screen.getByText("Élevée")).toBeInTheDocument();
    expect(screen.getByText("Moyenne")).toBeInTheDocument();
    expect(screen.getByText("Faible")).toBeInTheDocument();
  });

  it("renders confidence axis labels", () => {
    renderWithProviders(<RiskMatrix insights={[]} />);
    expect(screen.getByText("0%")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("renders one circle per insight", () => {
    const insights = [
      makeInsight({ id: "f-1" }),
      makeInsight({ id: "f-2", severity: "critical" }),
    ];
    renderWithProviders(<RiskMatrix insights={insights} />);
    // SVG circles — on vérifie via le conteneur SVG
    const svg = screen.getByRole("img");
    const circles = svg.querySelectorAll("circle");
    // 2 insights circles (pas les cercles de grille)
    expect(circles.length).toBeGreaterThanOrEqual(2);
  });

  it("shows tooltip on hover", () => {
    const insights = [makeInsight({ title: "Hover tooltip test" })];
    renderWithProviders(<RiskMatrix insights={insights} />);

    const svg = screen.getByRole("img");
    const circle = svg.querySelectorAll("circle").item(svg.querySelectorAll("circle").length - 1);
    fireEvent.mouseEnter(circle!);

    expect(screen.getByText("Hover tooltip test")).toBeInTheDocument();
  });

  it("calls onInsightClick when circle is clicked", () => {
    const insights = [makeInsight({ id: "f-clicked" })];
    renderWithProviders(
      <RiskMatrix insights={insights} onInsightClick={mockOnClick} />,
    );

    const svg = screen.getByRole("img");
    const circles = svg.querySelectorAll("circle");
    const lastCircle = circles.item(circles.length - 1);
    fireEvent.click(lastCircle!);

    expect(mockOnClick).toHaveBeenCalledWith("f-clicked");
  });

  it("reduces opacity for rejected insights", () => {
    const insights = [makeInsight({ status: "rejected" })];
    renderWithProviders(<RiskMatrix insights={insights} />);

    const svg = screen.getByRole("img");
    const circles = svg.querySelectorAll("circle");
    const lastCircle = circles.item(circles.length - 1);
    expect(lastCircle?.getAttribute("fill-opacity")).toBe("0.3");
  });
});
