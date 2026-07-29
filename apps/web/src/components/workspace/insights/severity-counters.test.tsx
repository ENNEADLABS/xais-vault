import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { SeverityCounters } from "./severity-counters";
import type { Insight } from "@/types/api";

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

function makeInsight(severity: Insight["severity"], id: string): Insight {
  return {
    id,
    workspace_id: "workspace-1",
    organization_id: "org-1",
    type: "red_flag",
    severity,
    confidence_score: 70,
    title: "Test",
    description: "Desc",
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
  };
}

describe("SeverityCounters", () => {
  it("renders counts per severity", () => {
    const insights = [
      makeInsight("critical", "f-1"),
      makeInsight("critical", "f-2"),
      makeInsight("high", "f-3"),
      makeInsight("medium", "f-4"),
      makeInsight("low", "f-5"),
    ];
    renderWithProviders(<SeverityCounters insights={insights} />);

    expect(screen.getByText("2 Critical")).toBeInTheDocument();
    expect(screen.getByText("1 High")).toBeInTheDocument();
    expect(screen.getByText("1 Medium")).toBeInTheDocument();
    expect(screen.getByText("1 Low")).toBeInTheDocument();
  });

  it("renders total count", () => {
    const insights = [
      makeInsight("critical", "f-1"),
      makeInsight("high", "f-2"),
    ];
    renderWithProviders(<SeverityCounters insights={insights} />);
    expect(screen.getByText("2 total")).toBeInTheDocument();
  });

  it("hides severity with zero count", () => {
    const insights = [makeInsight("critical", "f-1")];
    renderWithProviders(<SeverityCounters insights={insights} />);

    expect(screen.getByText("1 Critical")).toBeInTheDocument();
    expect(screen.queryByText(/High/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Medium/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Low/)).not.toBeInTheDocument();
  });

  it("renders nothing but total for empty insights", () => {
    renderWithProviders(<SeverityCounters insights={[]} />);
    expect(screen.getByText("0 total")).toBeInTheDocument();
  });
});
