import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const mockGet = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    setOrganizationId: vi.fn(),
  },
}));

import { useWorkspace } from "./use-workspace";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const DEAL = { id: "d-1", name: "Acme Corp", emoji: "🏢", status: "active" };

describe("useWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: DEAL });
  });

  it("appelle GET /workspaces/:id", async () => {
    const { result } = renderHook(() => useWorkspace("d-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/workspaces/d-1");
  });

  it("retourne les données du workspace", async () => {
    const { result } = renderHook(() => useWorkspace("d-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data?.name).toBe("Acme Corp");
  });

  it("n'appelle pas l'API si workspaceId est vide", () => {
    const { result } = renderHook(() => useWorkspace(""), { wrapper: createWrapper() });
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("isError sur échec API", async () => {
    mockGet.mockRejectedValue(new Error("Not found"));
    const { result } = renderHook(() => useWorkspace("d-999"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
