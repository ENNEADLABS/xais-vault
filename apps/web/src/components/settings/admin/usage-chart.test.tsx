import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { mockQueryLoading, mockQuerySuccess } from "@/tests/mocks/query-result";
import type { ApiResponse } from "@/lib/api";
import type { UsageStatsResponse } from "@/types/api";
import { UsageChart } from "./usage-chart";

type UsageResult = ApiResponse<UsageStatsResponse>;

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

vi.mock("@/lib/hooks/use-admin", () => ({
  useAdminUsage: vi.fn(),
}));

import { useAdminUsage } from "@/lib/hooks/use-admin";
const mockUseAdminUsage = vi.mocked(useAdminUsage);

const USAGE_DATA = {
  data: {
    months: [
      { month: "2026-01", operation: "chat", count: 50, input_tokens: 1000, output_tokens: 500, cost_usd: 0.05 },
      { month: "2026-01", operation: "scan", count: 20, input_tokens: 800, output_tokens: 300, cost_usd: 0.03 },
      { month: "2026-02", operation: "chat", count: 30, input_tokens: 600, output_tokens: 200, cost_usd: 0.02 },
    ],
    totals: { total_operations: 100, total_input_tokens: 2400, total_output_tokens: 1000, total_cost_usd: 0.10 },
  },
};

describe("UsageChart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche les skeletons en loading", () => {
    mockUseAdminUsage.mockReturnValue(mockQueryLoading<UsageResult>());

    const { container } = renderWithProviders(<UsageChart />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(4);
  });

  it("affiche le message vide quand pas de données", () => {
    mockUseAdminUsage.mockReturnValue(mockQuerySuccess<UsageResult>({
      data: { months: [], totals: { total_cost_usd: 0, total_input_tokens: 0, total_output_tokens: 0, total_operations: 0 } },
    }));

    renderWithProviders(<UsageChart />);
    expect(screen.getByText("noUsageData")).toBeInTheDocument();
  });

  it("affiche le message vide quand stats est undefined", () => {
    mockUseAdminUsage.mockReturnValue(mockQuerySuccess<UsageResult>({ data: null }));

    renderWithProviders(<UsageChart />);
    expect(screen.getByText("noUsageData")).toBeInTheDocument();
  });

  it("affiche les barres par mois avec totaux", () => {
    mockUseAdminUsage.mockReturnValue(mockQuerySuccess<UsageResult>(USAGE_DATA));

    renderWithProviders(<UsageChart />);
    expect(screen.getByText("2026-01")).toBeInTheDocument();
    expect(screen.getByText("2026-02")).toBeInTheDocument();
    expect(screen.getByText("70")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
  });

  it("affiche la légende des opérations", () => {
    mockUseAdminUsage.mockReturnValue(mockQuerySuccess<UsageResult>(USAGE_DATA));

    renderWithProviders(<UsageChart />);
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("Scan")).toBeInTheDocument();
    expect(screen.getByText("Vérif.")).toBeInTheDocument();
    expect(screen.getByText("Recherche")).toBeInTheDocument();
    expect(screen.getByText("Livrable")).toBeInTheDocument();
  });

  it("affiche les tooltips title sur les segments", () => {
    mockUseAdminUsage.mockReturnValue(mockQuerySuccess<UsageResult>(USAGE_DATA));

    renderWithProviders(<UsageChart />);
    expect(screen.getByTitle("Chat: 50")).toBeInTheDocument();
    expect(screen.getByTitle("Scan: 20")).toBeInTheDocument();
    expect(screen.getByTitle("Chat: 30")).toBeInTheDocument();
  });
});
