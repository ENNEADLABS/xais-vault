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

import { useInvestigations } from "./use-investigations";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe("useInvestigations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: [{ id: "inv-1", title: "Investigation 1", status: "pending" }] });
  });

  it("appelle GET /workspaces/:id/investigations/", async () => {
    const { result } = renderHook(() => useInvestigations("d-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/workspaces/d-1/investigations/");
  });

  it("retourne les investigations", async () => {
    const { result } = renderHook(() => useInvestigations("d-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data).toHaveLength(1);
  });

  it("n'appelle pas l'API si workspaceId est vide", () => {
    renderHook(() => useInvestigations(""), { wrapper: createWrapper() });
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("isError sur échec API", async () => {
    mockGet.mockRejectedValue(new Error("Forbidden"));
    const { result } = renderHook(() => useInvestigations("d-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
