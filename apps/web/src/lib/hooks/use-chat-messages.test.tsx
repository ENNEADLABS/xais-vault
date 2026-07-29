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

import { useChatMessages } from "./use-chat-messages";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe("useChatMessages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({
      data: {
        session: { id: "s-1", title: "Analyse Q1", workspace_id: "d-1" },
        messages: [{ id: "m-1", role: "user", content: "Bonjour" }],
      },
    });
  });

  it("appelle GET /workspaces/:workspaceId/chat/sessions/:sessionId", async () => {
    const { result } = renderHook(
      () => useChatMessages("d-1", "s-1"),
      { wrapper: createWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/workspaces/d-1/chat/sessions/s-1");
  });

  it("retourne la session et les messages", async () => {
    const { result } = renderHook(
      () => useChatMessages("d-1", "s-1"),
      { wrapper: createWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data?.session.id).toBe("s-1");
    expect(result.current.data?.data?.messages).toHaveLength(1);
  });

  it("n'appelle pas l'API si sessionId est null", () => {
    renderHook(() => useChatMessages("d-1", null), { wrapper: createWrapper() });
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("n'appelle pas l'API si sessionId est chaîne vide", () => {
    renderHook(() => useChatMessages("d-1", ""), { wrapper: createWrapper() });
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("isError sur échec API", async () => {
    mockGet.mockRejectedValue(new Error("Not found"));
    const { result } = renderHook(
      () => useChatMessages("d-1", "s-999"),
      { wrapper: createWrapper() },
    );
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
