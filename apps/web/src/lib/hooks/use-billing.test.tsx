import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    patch: vi.fn(),
    delete: vi.fn(),
    setOrganizationId: vi.fn(),
  },
}));

import { useBillingStatus, useCreateCheckout, useCreatePortal } from "./use-billing";
import type { BillingStatus } from "@/types/api";

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const BILLING_STATUS: BillingStatus = {
  plan: "trial",
  stripe_customer_id: null,
  stripe_subscription_id: null,
  trial_ends_at: "2026-03-31T00:00:00+00:00",
  limits: { max_workspaces: 20, max_analyses_per_month: 200 },
  current_usage: { workspaces_count: 3, analyses_this_month: 10 },
};

describe("useBillingStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: BILLING_STATUS });
  });

  it("appelle GET /billing/status", async () => {
    const { result } = renderHook(() => useBillingStatus(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/billing/status");
  });

  it("retourne les données de billing", async () => {
    const { result } = renderHook(() => useBillingStatus(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data?.plan).toBe("trial");
    expect(result.current.data?.data?.limits.max_workspaces).toBe(20);
  });

  it("démarre en loading", () => {
    const { result } = renderHook(() => useBillingStatus(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isLoading).toBe(true);
  });
});

describe("useCreateCheckout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.location pour éviter l'erreur jsdom
    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });
  });

  it("appelle POST /billing/checkout avec les bons paramètres", async () => {
    mockPost.mockResolvedValue({ data: { url: "https://checkout.stripe.com/cs_test" } });

    const { result } = renderHook(() => useCreateCheckout(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      price_id: "price_starter_123",
      success_url: "https://app.example.com/billing?success=true",
      cancel_url: "https://app.example.com/billing",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPost).toHaveBeenCalledWith("/billing/checkout", {
      price_id: "price_starter_123",
      success_url: "https://app.example.com/billing?success=true",
      cancel_url: "https://app.example.com/billing",
    });
  });

  it("redirige vers l'URL Stripe après succès", async () => {
    mockPost.mockResolvedValue({ data: { url: "https://checkout.stripe.com/cs_test" } });

    const { result } = renderHook(() => useCreateCheckout(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      price_id: "price_team_456",
      success_url: "https://app.example.com/success",
      cancel_url: "https://app.example.com/cancel",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(window.location.href).toBe("https://checkout.stripe.com/cs_test");
  });

  it("gère data null sans crash", async () => {
    mockPost.mockResolvedValue({ data: null });

    const { result } = renderHook(() => useCreateCheckout(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      price_id: "price_starter_123",
      success_url: "https://app.example.com/success",
      cancel_url: "https://app.example.com/cancel",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // Doit rediriger vers "" (fallback) sans erreur
    expect(window.location.href).toBe("");
  });
});

describe("useCreatePortal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, "location", {
      value: { href: "" },
      writable: true,
    });
  });

  it("appelle POST /billing/portal avec return_url", async () => {
    mockPost.mockResolvedValue({ data: { url: "https://billing.stripe.com/session" } });

    const { result } = renderHook(() => useCreatePortal(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("https://app.example.com/settings");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPost).toHaveBeenCalledWith("/billing/portal", {
      return_url: "https://app.example.com/settings",
    });
  });

  it("redirige vers le portail Stripe après succès", async () => {
    mockPost.mockResolvedValue({ data: { url: "https://billing.stripe.com/session" } });

    const { result } = renderHook(() => useCreatePortal(), {
      wrapper: createWrapper(),
    });

    result.current.mutate("https://app.example.com/settings");

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(window.location.href).toBe("https://billing.stripe.com/session");
  });
});
