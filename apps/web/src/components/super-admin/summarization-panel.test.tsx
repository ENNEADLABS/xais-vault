import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { SummarizationPanel } from "./summarization-panel";

const mockUseSummarizationStats = vi.fn();

vi.mock("@/lib/hooks/use-super-admin", () => ({
  useSummarizationStats: () => mockUseSummarizationStats(),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

describe("SummarizationPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le chargement", () => {
    mockUseSummarizationStats.mockReturnValue({ data: undefined, isLoading: true });

    renderWithProviders(<SummarizationPanel />);
    expect(screen.getByText("loading")).toBeInTheDocument();
  });

  it("affiche 'aucune donnee' quand total_count est 0", () => {
    mockUseSummarizationStats.mockReturnValue({
      data: {
        total_count: 0,
        count_24h: 0,
        total_cost_usd: 0,
        cost_24h_usd: 0,
        avg_cost_usd: 0,
        avg_input_tokens: 0,
        avg_output_tokens: 0,
      },
      isLoading: false,
    });

    renderWithProviders(<SummarizationPanel />);
    expect(screen.getByText("noData")).toBeInTheDocument();
  });

  it("affiche les 3 KPI cards avec les valeurs", () => {
    mockUseSummarizationStats.mockReturnValue({
      data: {
        total_count: 42,
        count_24h: 5,
        total_cost_usd: 0.0523,
        cost_24h_usd: 0.0062,
        avg_cost_usd: 0.001245,
        avg_input_tokens: 850,
        avg_output_tokens: 320,
      },
      isLoading: false,
    });

    renderWithProviders(<SummarizationPanel />);
    expect(screen.getByText("totalCount")).toBeInTheDocument();
    expect(screen.getByText("totalCost")).toBeInTheDocument();
    expect(screen.getByText("avgCost")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("$0.0523")).toBeInTheDocument();
  });

  it("affiche l'alerte quand cost_24h depasse le seuil", () => {
    mockUseSummarizationStats.mockReturnValue({
      data: {
        total_count: 100,
        count_24h: 50,
        total_cost_usd: 5.0,
        cost_24h_usd: 1.5,
        avg_cost_usd: 0.05,
        avg_input_tokens: 900,
        avg_output_tokens: 400,
      },
      isLoading: false,
    });

    renderWithProviders(<SummarizationPanel />);
    expect(screen.getByText(/alertThreshold/)).toBeInTheDocument();
  });

  it("n'affiche pas l'alerte quand cost_24h est sous le seuil", () => {
    mockUseSummarizationStats.mockReturnValue({
      data: {
        total_count: 10,
        count_24h: 2,
        total_cost_usd: 0.01,
        cost_24h_usd: 0.002,
        avg_cost_usd: 0.001,
        avg_input_tokens: 500,
        avg_output_tokens: 200,
      },
      isLoading: false,
    });

    renderWithProviders(<SummarizationPanel />);
    expect(screen.queryByText(/alertThreshold/)).not.toBeInTheDocument();
  });

  it("affiche les tokens moyens", () => {
    mockUseSummarizationStats.mockReturnValue({
      data: {
        total_count: 10,
        count_24h: 1,
        total_cost_usd: 0.01,
        cost_24h_usd: 0.001,
        avg_cost_usd: 0.001,
        avg_input_tokens: 850,
        avg_output_tokens: 320,
      },
      isLoading: false,
    });

    renderWithProviders(<SummarizationPanel />);
    expect(screen.getByText("avgInputTokens")).toBeInTheDocument();
    expect(screen.getByText("avgOutputTokens")).toBeInTheDocument();
    expect(screen.getByText("850")).toBeInTheDocument();
    expect(screen.getByText("320")).toBeInTheDocument();
  });
});
