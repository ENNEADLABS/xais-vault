import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const mockGet = vi.fn();
const mockPatch = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
    post: vi.fn(),
    delete: vi.fn(),
    setOrganizationId: vi.fn(),
  },
}));

import { useInsights, useUpdateInsight } from "./use-insights";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe("useInsights", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: [] });
  });

  it("appelle GET /workspaces/:id/insights/ sans filtres", async () => {
    const { result } = renderHook(() => useInsights("d-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/workspaces/d-1/insights/");
  });

  it("ajoute le filtre type dans la querystring", async () => {
    const { result } = renderHook(
      () => useInsights("d-1", { type: "red_flag" }),
      { wrapper: createWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith(expect.stringContaining("type=red_flag"));
  });

  it("ajoute le filtre severity dans la querystring", async () => {
    const { result } = renderHook(
      () => useInsights("d-1", { severity: "high" }),
      { wrapper: createWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith(expect.stringContaining("severity=high"));
  });

  it("combine plusieurs filtres", async () => {
    const { result } = renderHook(
      () => useInsights("d-1", { type: "red_flag", severity: "critical", status: "pending" }),
      { wrapper: createWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const url = mockGet.mock.calls[0]![0] as string;
    expect(url).toContain("type=red_flag");
    expect(url).toContain("severity=critical");
    expect(url).toContain("status=pending");
  });

  it("n'appelle pas l'API si workspaceId est vide", () => {
    renderHook(() => useInsights(""), { wrapper: createWrapper() });
    expect(mockGet).not.toHaveBeenCalled();
  });
});

describe("useUpdateInsight — mapping status → action", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPatch.mockResolvedValue({ data: { id: "f-1", status: "confirmed" } });
  });

  it("mappe 'confirmed' → action 'confirm'", async () => {
    const { result } = renderHook(() => useUpdateInsight("d-1"), { wrapper: createWrapper() });
    result.current.mutate({ insightId: "f-1", update: { status: "confirmed" } });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPatch).toHaveBeenCalledWith(
      "/workspaces/d-1/insights/f-1",
      { action: "confirm" },
    );
  });

  it("mappe 'rejected' → action 'reject'", async () => {
    const { result } = renderHook(() => useUpdateInsight("d-1"), { wrapper: createWrapper() });
    result.current.mutate({ insightId: "f-1", update: { status: "rejected" } });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPatch).toHaveBeenCalledWith(
      "/workspaces/d-1/insights/f-1",
      { action: "reject" },
    );
  });

  it("mappe 'investigating' → action 'investigate'", async () => {
    const { result } = renderHook(() => useUpdateInsight("d-1"), { wrapper: createWrapper() });
    result.current.mutate({ insightId: "f-1", update: { status: "investigating" } });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPatch).toHaveBeenCalledWith(
      "/workspaces/d-1/insights/f-1",
      { action: "investigate" },
    );
  });

  it("fallback sur le status brut si non mappé", async () => {
    const { result } = renderHook(() => useUpdateInsight("d-1"), { wrapper: createWrapper() });
    // @ts-expect-error — statut inconnu intentionnel pour tester le fallback
    result.current.mutate({ insightId: "f-1", update: { status: "unknown_status" } });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPatch).toHaveBeenCalledWith(
      "/workspaces/d-1/insights/f-1",
      { action: "unknown_status" },
    );
  });
});
