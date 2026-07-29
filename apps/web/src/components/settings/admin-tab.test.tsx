import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { AdminTab } from "./admin-tab";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock tous les sous-composants pour isoler le test
vi.mock("./admin/org-overview", () => ({
  OrgOverview: () => <div data-testid="org-overview">OrgOverview</div>,
}));

vi.mock("./admin/usage-chart", () => ({
  UsageChart: () => <div data-testid="usage-chart">UsageChart</div>,
}));

vi.mock("./admin/cost-breakdown", () => ({
  CostBreakdown: () => <div data-testid="cost-breakdown">CostBreakdown</div>,
}));

vi.mock("./admin/activity-log", () => ({
  ActivityLog: () => <div data-testid="activity-log">ActivityLog</div>,
}));

vi.mock("./admin/api-key-usage", () => ({
  ApiKeyUsage: () => <div data-testid="api-key-usage">ApiKeyUsage</div>,
}));

describe("AdminTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le titre et la description", () => {
    renderWithProviders(<AdminTab />);
    expect(screen.getByText("title")).toBeInTheDocument();
    expect(screen.getByText("description")).toBeInTheDocument();
  });

  it("affiche les 5 titres de section", () => {
    renderWithProviders(<AdminTab />);
    expect(screen.getByText("overviewSection")).toBeInTheDocument();
    expect(screen.getByText("usageSection")).toBeInTheDocument();
    expect(screen.getByText("costsSection")).toBeInTheDocument();
    expect(screen.getByText("activitySection")).toBeInTheDocument();
    expect(screen.getByText("apiKeysSection")).toBeInTheDocument();
  });

  it("rend tous les sous-composants", () => {
    renderWithProviders(<AdminTab />);
    expect(screen.getByTestId("org-overview")).toBeInTheDocument();
    expect(screen.getByTestId("usage-chart")).toBeInTheDocument();
    expect(screen.getByTestId("cost-breakdown")).toBeInTheDocument();
    expect(screen.getByTestId("activity-log")).toBeInTheDocument();
    expect(screen.getByTestId("api-key-usage")).toBeInTheDocument();
  });
});
