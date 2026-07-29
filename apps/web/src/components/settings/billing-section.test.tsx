import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { mockQueryLoading, mockQuerySuccess } from "@/tests/mocks/query-result";
import type { ApiResponse } from "@/lib/api";
import { BillingSection } from "./billing-section";
import type { BillingStatus } from "@/types/api";

type BillingResult = ApiResponse<BillingStatus>;

vi.mock("@/lib/hooks/use-billing", () => ({
  useBillingStatus: vi.fn(),
  useCreateCheckout: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useCreatePortal: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

import { useBillingStatus } from "@/lib/hooks/use-billing";

function makeBillingStatus(overrides: Partial<BillingStatus> = {}): BillingStatus {
  return {
    plan: "starter",
    stripe_customer_id: null,
    stripe_subscription_id: null,
    trial_ends_at: null,
    limits: { max_workspaces: 5, max_analyses_per_month: 50 },
    current_usage: { workspaces_count: 2, analyses_this_month: 10 },
    ...overrides,
  };
}

describe("BillingSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le skeleton en chargement", () => {
    vi.mocked(useBillingStatus).mockReturnValue(mockQueryLoading<BillingResult>());

    const { container } = renderWithProviders(<BillingSection />);
    const skeletons = container.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("affiche le badge du plan actuel", () => {
    vi.mocked(useBillingStatus).mockReturnValue(
      mockQuerySuccess<BillingResult>({ data: makeBillingStatus({ plan: "team" }) }),
    );

    renderWithProviders(<BillingSection />);
    expect(screen.getByText("Team")).toBeInTheDocument();
  });

  it("affiche le badge du plan Premium", () => {
    vi.mocked(useBillingStatus).mockReturnValue(
      mockQuerySuccess<BillingResult>({ data: makeBillingStatus({ plan: "premium" }) }),
    );

    renderWithProviders(<BillingSection />);
    expect(screen.getByText("Premium")).toBeInTheDocument();
  });

  it("affiche le badge Trial pour plan trial", () => {
    vi.mocked(useBillingStatus).mockReturnValue(
      mockQuerySuccess({
        data: makeBillingStatus({
          plan: "trial",
          trial_ends_at: "2026-03-31T00:00:00+00:00",
          limits: { max_workspaces: 20, max_analyses_per_month: 200 },
        }),
      }),
    );

    renderWithProviders(<BillingSection />);
    expect(screen.getByText("Essai gratuit")).toBeInTheDocument();
  });

  it("affiche les barres d'usage avec les valeurs correctes", () => {
    vi.mocked(useBillingStatus).mockReturnValue(
      mockQuerySuccess({
        data: makeBillingStatus({
          current_usage: { workspaces_count: 3, analyses_this_month: 25 },
          limits: { max_workspaces: 5, max_analyses_per_month: 50 },
        }),
      }),
    );

    renderWithProviders(<BillingSection />);
    expect(screen.getByText("3 / 5")).toBeInTheDocument();
    expect(screen.getByText("25 / 50")).toBeInTheDocument();
  });

  it("affiche 'illimité' pour plan Enterprise", () => {
    vi.mocked(useBillingStatus).mockReturnValue(
      mockQuerySuccess({
        data: makeBillingStatus({
          plan: "enterprise",
          limits: { max_workspaces: null, max_analyses_per_month: null },
          current_usage: { workspaces_count: 42, analyses_this_month: 999 },
        }),
      }),
    );

    renderWithProviders(<BillingSection />);
    const unlimited = screen.getAllByText(/illimité/i);
    expect(unlimited.length).toBeGreaterThan(0);
  });

  it("affiche le bouton 'Gérer l'abonnement' quand subscription active", () => {
    vi.mocked(useBillingStatus).mockReturnValue(
      mockQuerySuccess({
        data: makeBillingStatus({
          plan: "team",
          stripe_subscription_id: "sub_test_123",
        }),
      }),
    );

    renderWithProviders(<BillingSection />);
    expect(screen.getByText(/Gérer l.abonnement/)).toBeInTheDocument();
  });

  it("affiche les boutons Upgrade quand pas de subscription", () => {
    vi.mocked(useBillingStatus).mockReturnValue(
      mockQuerySuccess({
        data: makeBillingStatus({
          plan: "starter",
          stripe_subscription_id: null,
        }),
      }),
    );

    renderWithProviders(<BillingSection />);
    expect(screen.getByText(/Premium/)).toBeInTheDocument();
    expect(screen.getByText(/Team/)).toBeInTheDocument();
  });

  it("affiche le message Enterprise pour plan enterprise", () => {
    vi.mocked(useBillingStatus).mockReturnValue(
      mockQuerySuccess({
        data: makeBillingStatus({
          plan: "enterprise",
          limits: { max_workspaces: null, max_analyses_per_month: null },
        }),
      }),
    );

    renderWithProviders(<BillingSection />);
    expect(screen.getByText(/Plan Enterprise/)).toBeInTheDocument();
  });

  it("n'affiche rien quand data est null", () => {
    vi.mocked(useBillingStatus).mockReturnValue(
      mockQuerySuccess<BillingResult>({ data: null }),
    );

    const { container } = renderWithProviders(<BillingSection />);
    expect(container.firstChild).toBeNull();
  });
});
