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

import { useWorkspaces, useCreateWorkspace } from "./use-workspaces";

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

describe("useWorkspaces", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({
      data: [],
      total: 0,
      page: 1,
      per_page: 20,
      pages: 0,
    });
  });

  it("fetches workspaces with default params (page=1)", async () => {
    const { result } = renderHook(() => useWorkspaces(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/workspaces/?page=1");
  });

  it("fetches workspaces with status filter", async () => {
    const { result } = renderHook(() => useWorkspaces({ status: "active" }), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith(
      expect.stringContaining("status=active"),
    );
  });

  it("fetches workspaces with custom page", async () => {
    const { result } = renderHook(() => useWorkspaces({ page: 3 }), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith(expect.stringContaining("page=3"));
  });

  it("returns isLoading initially", () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    const { result } = renderHook(() => useWorkspaces(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isLoading).toBe(true);
  });

  it("returns data after resolution", async () => {
    const workspaces = [{ id: "d-1", name: "Acme" }];
    mockGet.mockResolvedValue({
      data: workspaces,
      total: 1,
      page: 1,
      per_page: 20,
      pages: 1,
    });
    const { result } = renderHook(() => useWorkspaces(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data).toEqual(workspaces);
  });

  it("returns error on API failure", async () => {
    mockGet.mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useWorkspaces(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useCreateWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPost.mockResolvedValue({
      data: { id: "workspace-1", name: "Test" },
    });
  });

  it("calls POST /workspaces/ with input", async () => {
    const { result } = renderHook(() => useCreateWorkspace(), {
      wrapper: createWrapper(),
    });
    result.current.mutate({ name: "Acme Corp", emoji: "🚀" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPost).toHaveBeenCalledWith("/workspaces/", {
      name: "Acme Corp",
      emoji: "🚀",
    });
  });

  it("invalidates workspaces query on success", async () => {
    const qc = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    const spy = vi.spyOn(qc, "invalidateQueries");
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useCreateWorkspace(), { wrapper });
    result.current.mutate({ name: "Test", emoji: "📦" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledWith({ queryKey: ["workspaces"] });
  });

  it("returns error on failure", async () => {
    mockPost.mockRejectedValue(new Error("Server error"));
    const { result } = renderHook(() => useCreateWorkspace(), {
      wrapper: createWrapper(),
    });
    result.current.mutate({ name: "Fail", emoji: "💥" });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
