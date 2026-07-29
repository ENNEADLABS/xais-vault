import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { mockQueryLoading, mockQuerySuccess } from "@/tests/mocks/query-result";
import type { ApiResponse } from "@/lib/api";
import type { UsageStatsResponse } from "@/types/api";
import { CostBreakdown } from "./cost-breakdown";

type UsageResult = ApiResponse<UsageStatsResponse>;

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/hooks/use-admin", () => ({
  useAdminUsage: vi.fn(),
}));

import { useAdminUsage } from "@/lib/hooks/use-admin";
const mockUseAdminUsage = vi.mocked(useAdminUsage);

const USAGE_DATA = {
  data: {
    months: [
      { month: "2026-01", operation: "chat", count: 50, input_tokens: 10000, output_tokens: 5000, cost_usd: 0.1234 },
      { month: "2026-01", operation: "scan", count: 20, input_tokens: 8000, output_tokens: 3000, cost_usd: 0.0567 },
      { month: "2026-02", operation: "chat", count: 30, input_tokens: 6000, output_tokens: 2000, cost_usd: 0.0890 },
    ],
    totals: {
      total_operations: 100,
      total_input_tokens: 24000,
      total_output_tokens: 10000,
      total_cost_usd: 0.2691,
    },
  },
};

describe("CostBreakdown", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche les skeletons en loading", () => {
    mockUseAdminUsage.mockReturnValue(mockQueryLoading<UsageResult>());

    const { container } = renderWithProviders(<CostBreakdown />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(5);
  });

  it("affiche le message vide quand pas de données", () => {
    mockUseAdminUsage.mockReturnValue(mockQuerySuccess<UsageResult>({
      data: { months: [], totals: { total_cost_usd: 0, total_input_tokens: 0, total_output_tokens: 0, total_operations: 0 } },
    }));

    renderWithProviders(<CostBreakdown />);
    expect(screen.getByText("noUsageData")).toBeInTheDocument();
  });

  it("affiche les en-têtes de colonnes", () => {
    mockUseAdminUsage.mockReturnValue(mockQuerySuccess<UsageResult>(USAGE_DATA));

    renderWithProviders(<CostBreakdown />);
    expect(screen.getByText("operation")).toBeInTheDocument();
    expect(screen.getByText("requests")).toBeInTheDocument();
    expect(screen.getByText("tokensIn")).toBeInTheDocument();
    expect(screen.getByText("tokensOut")).toBeInTheDocument();
    expect(screen.getByText("cost")).toBeInTheDocument();
  });

  it("affiche les lignes agrégées par opération triées par coût", () => {
    mockUseAdminUsage.mockReturnValue(mockQuerySuccess<UsageResult>(USAGE_DATA));

    renderWithProviders(<CostBreakdown />);
    expect(screen.getByText("chat")).toBeInTheDocument();
    expect(screen.getByText("scan")).toBeInTheDocument();
    expect(screen.getByText("$0.2124")).toBeInTheDocument();
    expect(screen.getByText("$0.0567")).toBeInTheDocument();
  });

  it("affiche la ligne total en footer", () => {
    mockUseAdminUsage.mockReturnValue(mockQuerySuccess<UsageResult>(USAGE_DATA));

    renderWithProviders(<CostBreakdown />);
    expect(screen.getByText("total")).toBeInTheDocument();
    expect(screen.getByText("$0.2691")).toBeInTheDocument();
  });
});
