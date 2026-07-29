import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { mockQueryLoading, mockQuerySuccess, mockQueryError } from "@/tests/mocks/query-result";
import type { ApiResponse } from "@/lib/api";
import type { OrgOverviewResponse } from "@/types/api";
import { OrgOverview } from "./org-overview";

type OverviewResult = ApiResponse<OrgOverviewResponse>;

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/hooks/use-admin", () => ({
  useAdminOverview: vi.fn(),
}));

import { useAdminOverview } from "@/lib/hooks/use-admin";
const mockUseAdminOverview = vi.mocked(useAdminOverview);

const OVERVIEW_DATA: OverviewResult = {
  data: {
    name: "XAIS Test",
    plan: "premium",
    member_count: 5,
    workspace_count: 12,
    source_count: 34,
    insight_count: 89,
    trial_ends_at: null,
  },
};

describe("OrgOverview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche les skeletons en loading", () => {
    mockUseAdminOverview.mockReturnValue(mockQueryLoading<OverviewResult>());

    const { container } = renderWithProviders(<OrgOverview />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(4);
  });

  it("affiche le message d'erreur quand isError", () => {
    mockUseAdminOverview.mockReturnValue(mockQueryError<OverviewResult>());

    renderWithProviders(<OrgOverview />);
    expect(screen.getByText("overviewError")).toBeInTheDocument();
  });

  it("affiche le message d'erreur quand data est undefined", () => {
    mockUseAdminOverview.mockReturnValue(mockQuerySuccess<OverviewResult>({ data: null }));

    renderWithProviders(<OrgOverview />);
    expect(screen.getByText("overviewError")).toBeInTheDocument();
  });

  it("affiche les 4 stat cards avec les bonnes valeurs", () => {
    mockUseAdminOverview.mockReturnValue(mockQuerySuccess<OverviewResult>(OVERVIEW_DATA));

    renderWithProviders(<OrgOverview />);
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("34")).toBeInTheDocument();
    expect(screen.getByText("89")).toBeInTheDocument();
  });

  it("affiche les labels traduits", () => {
    mockUseAdminOverview.mockReturnValue(mockQuerySuccess<OverviewResult>(OVERVIEW_DATA));

    renderWithProviders(<OrgOverview />);
    expect(screen.getByText("members")).toBeInTheDocument();
    expect(screen.getByText("workspaces")).toBeInTheDocument();
    expect(screen.getByText("sources")).toBeInTheDocument();
    expect(screen.getByText("insights")).toBeInTheDocument();
  });
});
