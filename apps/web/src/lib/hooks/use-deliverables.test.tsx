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

import { useDeliverables, useCreateDeliverable } from "./use-deliverables";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const DELIVERABLE = { id: "del-1", type: "investment_memo", name: "Mémo Q1", status: "pending", workspace_id: "d-1" };

describe("useDeliverables", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: [DELIVERABLE] });
  });

  it("appelle GET /workspaces/:id/deliverables/", async () => {
    const { result } = renderHook(() => useDeliverables("d-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/workspaces/d-1/deliverables/");
  });

  it("retourne les livrables", async () => {
    const { result } = renderHook(() => useDeliverables("d-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data?.[0]?.type).toBe("investment_memo");
  });

  it("n'appelle pas l'API si workspaceId est vide", () => {
    renderHook(() => useDeliverables(""), { wrapper: createWrapper() });
    expect(mockGet).not.toHaveBeenCalled();
  });
});

describe("useCreateDeliverable", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPost.mockResolvedValue({ data: DELIVERABLE });
  });

  it("appelle POST /workspaces/:id/deliverables/ avec les données", async () => {
    const { result } = renderHook(() => useCreateDeliverable("d-1"), { wrapper: createWrapper() });
    result.current.mutate({ type: "investment_memo", name: "Mémo Q1" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPost).toHaveBeenCalledWith("/workspaces/d-1/deliverables/", {
      type: "investment_memo",
      name: "Mémo Q1",
    });
  });

  it("accepte les options optionnelles", async () => {
    const { result } = renderHook(() => useCreateDeliverable("d-1"), { wrapper: createWrapper() });
    result.current.mutate({ type: "dd_report", name: "Rapport annuel", options: { sections: ["exec_summary"] } });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPost).toHaveBeenCalledWith("/workspaces/d-1/deliverables/", expect.objectContaining({
      options: { sections: ["exec_summary"] },
    }));
  });

  it("isError sur échec POST", async () => {
    mockPost.mockRejectedValue(new Error("Plan limit reached"));
    const { result } = renderHook(() => useCreateDeliverable("d-1"), { wrapper: createWrapper() });
    result.current.mutate({ type: "investment_memo", name: "Fail" });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
