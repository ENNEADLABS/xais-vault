import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { HealthPanel } from "./health-panel";

const mockUseErrorLog = vi.fn();
const mockUsePlatformOverview = vi.fn();

vi.mock("@/lib/hooks/use-super-admin", () => ({
  useErrorLog: () => mockUseErrorLog(),
  usePlatformOverview: () => mockUsePlatformOverview(),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

describe("HealthPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le chargement", () => {
    mockUseErrorLog.mockReturnValue({ data: undefined, isLoading: true });
    mockUsePlatformOverview.mockReturnValue({ data: undefined });

    renderWithProviders(<HealthPanel />);
    expect(screen.getByText("loading")).toBeInTheDocument();
  });

  it("affiche 'aucune erreur' quand la liste est vide", () => {
    mockUseErrorLog.mockReturnValue({ data: [], isLoading: false });
    mockUsePlatformOverview.mockReturnValue({
      data: { job_success_rate_7d: 100, failed_jobs_24h: 0 },
    });

    renderWithProviders(<HealthPanel />);
    expect(screen.getByText("noErrors")).toBeInTheDocument();
  });

  it("affiche les erreurs avec les détails", () => {
    mockUseErrorLog.mockReturnValue({
      data: [
        {
          id: "1",
          type: "index_source",
          org_name: "Acme",
          workspace_name: "Workspace1",
          error_message: "PDF corrupted",
          attempts: 3,
          created_at: "2026-03-24T08:00:00Z",
          failed_at: "2026-03-24T08:01:00Z",
        },
      ],
      isLoading: false,
    });
    mockUsePlatformOverview.mockReturnValue({
      data: { job_success_rate_7d: 90, failed_jobs_24h: 1 },
    });

    renderWithProviders(<HealthPanel />);
    expect(screen.getByText("index_source")).toBeInTheDocument();
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getByText("PDF corrupted")).toBeInTheDocument();
  });

  it("affiche le taux de succès et les failed 24h", () => {
    mockUseErrorLog.mockReturnValue({ data: [], isLoading: false });
    mockUsePlatformOverview.mockReturnValue({
      data: { job_success_rate_7d: 95.5, failed_jobs_24h: 2 },
    });

    renderWithProviders(<HealthPanel />);
    expect(screen.getByText("95.5%")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});
