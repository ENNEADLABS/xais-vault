import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
    setOrganizationId: vi.fn(),
  },
}));

import {
  useApiKeys,
  useApiKey,
  useCreateApiKey,
  useUpdateApiKey,
  useRevokeApiKey,
  useRotateApiKey,
} from "./use-api-keys";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const KEY = { id: "k-1", name: "CI Key", key_prefix: "xv_live_", is_active: true };

describe("useApiKeys", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: [KEY], total: 1, page: 1, per_page: 20, pages: 1 });
  });

  it("appelle GET /api-keys/?page=1 par défaut", async () => {
    const { result } = renderHook(() => useApiKeys(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/api-keys/?page=1");
  });

  it("passe la page personnalisée", async () => {
    const { result } = renderHook(() => useApiKeys(2), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/api-keys/?page=2");
  });
});

describe("useApiKey", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: { ...KEY, last_used_at: null } });
  });

  it("appelle GET /api-keys/:id", async () => {
    const { result } = renderHook(() => useApiKey("k-1"), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/api-keys/k-1");
  });

  it("n'appelle pas l'API si keyId est vide", () => {
    renderHook(() => useApiKey(""), { wrapper: createWrapper() });
    expect(mockGet).not.toHaveBeenCalled();
  });
});

describe("useCreateApiKey", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPost.mockResolvedValue({ data: { ...KEY, key: "xv_live_abc123" } }); // gitleaks:allow
  });

  it("appelle POST /api-keys/ avec les données", async () => {
    const { result } = renderHook(() => useCreateApiKey(), { wrapper: createWrapper() });
    result.current.mutate({ name: "CI Key", rpm_limit: 60, rpd_limit: 1000 });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPost).toHaveBeenCalledWith("/api-keys/", {
      name: "CI Key",
      rpm_limit: 60,
      rpd_limit: 1000,
    });
  });

  it("isError sur échec POST", async () => {
    mockPost.mockRejectedValue(new Error("Conflict"));
    const { result } = renderHook(() => useCreateApiKey(), { wrapper: createWrapper() });
    result.current.mutate({ name: "Fail" });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useUpdateApiKey", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPatch.mockResolvedValue({ data: { ...KEY, is_active: false } });
  });

  it("appelle PATCH /api-keys/:id avec les données", async () => {
    const { result } = renderHook(() => useUpdateApiKey("k-1"), { wrapper: createWrapper() });
    result.current.mutate({ is_active: false });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPatch).toHaveBeenCalledWith("/api-keys/k-1", { is_active: false });
  });
});

describe("useRevokeApiKey", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDelete.mockResolvedValue({});
  });

  it("appelle DELETE /api-keys/:id", async () => {
    const { result } = renderHook(() => useRevokeApiKey(), { wrapper: createWrapper() });
    result.current.mutate("k-1");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockDelete).toHaveBeenCalledWith("/api-keys/k-1");
  });
});

describe("useRotateApiKey", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPost.mockResolvedValue({ data: { ...KEY, key: "xv_live_newkey" } }); // gitleaks:allow
  });

  it("appelle POST /api-keys/:id/rotate", async () => {
    const { result } = renderHook(() => useRotateApiKey(), { wrapper: createWrapper() });
    result.current.mutate("k-1");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPost).toHaveBeenCalledWith("/api-keys/k-1/rotate");
  });
});
