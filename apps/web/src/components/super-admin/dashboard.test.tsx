import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { SuperAdminDashboard } from "./dashboard";

// Mock hooks
const mockUseSuperAdminCheck = vi.fn();

vi.mock("@/lib/hooks/use-super-admin", () => ({
  useSuperAdminCheck: () => mockUseSuperAdminCheck(),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

// Mock child components
vi.mock("./overview-cards", () => ({
  OverviewCards: () => <div data-testid="overview-cards">OverviewCards</div>,
}));
vi.mock("./activity-feed", () => ({
  ActivityFeed: () => <div data-testid="activity-feed">ActivityFeed</div>,
}));
vi.mock("./health-panel", () => ({
  HealthPanel: () => <div data-testid="health-panel">HealthPanel</div>,
}));

describe("SuperAdminDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le chargement quand la vérification est en cours", () => {
    mockUseSuperAdminCheck.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    renderWithProviders(<SuperAdminDashboard />);
    expect(screen.getByText("loading")).toBeInTheDocument();
  });

  it("affiche accès refusé pour un non-admin", () => {
    mockUseSuperAdminCheck.mockReturnValue({
      data: { is_super_admin: false },
      isLoading: false,
    });

    renderWithProviders(<SuperAdminDashboard />);
    expect(screen.getByText("accessDenied")).toBeInTheDocument();
  });

  it("affiche le dashboard avec les onglets pour un super-admin", () => {
    mockUseSuperAdminCheck.mockReturnValue({
      data: { is_super_admin: true },
      isLoading: false,
    });

    renderWithProviders(<SuperAdminDashboard />);
    expect(screen.getByText("title")).toBeInTheDocument();
    expect(screen.getByText("tabs.activity")).toBeInTheDocument();
    expect(screen.getByText("tabs.health")).toBeInTheDocument();
    expect(screen.getByText("tabs.overview")).toBeInTheDocument();
  });

  it("affiche l'onglet Activity par défaut", () => {
    mockUseSuperAdminCheck.mockReturnValue({
      data: { is_super_admin: true },
      isLoading: false,
    });

    renderWithProviders(<SuperAdminDashboard />);
    expect(screen.getByTestId("activity-feed")).toBeInTheDocument();
  });

  it("bascule vers l'onglet Overview au clic", () => {
    mockUseSuperAdminCheck.mockReturnValue({
      data: { is_super_admin: true },
      isLoading: false,
    });

    renderWithProviders(<SuperAdminDashboard />);

    // Vérifie que le feed est affiché par défaut
    expect(screen.getByTestId("activity-feed")).toBeInTheDocument();
  });
});
