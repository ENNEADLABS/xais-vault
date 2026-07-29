import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const mockGet = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
    post: vi.fn(),
    setOrganizationId: vi.fn(),
  },
}));

import { useChatSessions, useRenameSession, useDeleteSession } from "./use-chat-sessions";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const SESSION = { id: "s-1", title: "Analyse Q1", workspace_id: "d-1" };

describe("useChatSessions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: [SESSION] });
  });

  it("appelle GET /workspaces/:id/chat/sessions", async () => {
    const { result } = renderHook(() => useChatSessions("d-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/workspaces/d-1/chat/sessions");
  });

  it("retourne les sessions", async () => {
    const { result } = renderHook(() => useChatSessions("d-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data).toHaveLength(1);
    expect(result.current.data?.data?.[0]?.title).toBe("Analyse Q1");
  });

  it("n'appelle pas l'API si workspaceId est vide", () => {
    renderHook(() => useChatSessions(""), { wrapper: createWrapper() });
    expect(mockGet).not.toHaveBeenCalled();
  });
});

describe("useRenameSession", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPatch.mockResolvedValue({ data: { ...SESSION, title: "Nouveau titre" } });
  });

  it("appelle PATCH /workspaces/:id/chat/sessions/:sessionId", async () => {
    const { result } = renderHook(() => useRenameSession("d-1"), { wrapper: createWrapper() });
    result.current.mutate({ sessionId: "s-1", title: "Nouveau titre" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPatch).toHaveBeenCalledWith(
      "/workspaces/d-1/chat/sessions/s-1",
      { title: "Nouveau titre" },
    );
  });
});

describe("useDeleteSession", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDelete.mockResolvedValue({});
  });

  it("appelle DELETE /workspaces/:id/chat/sessions/:sessionId", async () => {
    const { result } = renderHook(() => useDeleteSession("d-1"), { wrapper: createWrapper() });
    result.current.mutate("s-1");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockDelete).toHaveBeenCalledWith("/workspaces/d-1/chat/sessions/s-1");
  });

  it("isError sur échec DELETE", async () => {
    mockDelete.mockRejectedValue(new Error("Not found"));
    const { result } = renderHook(() => useDeleteSession("d-1"), { wrapper: createWrapper() });
    result.current.mutate("s-999");
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
