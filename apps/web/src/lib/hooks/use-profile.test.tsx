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

import { useProfile, useUpdateProfile } from "./use-profile";

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

const PROFILE = { id: "u-1", display_name: "Example User", email: "x@test.com", avatar_url: null };

describe("useProfile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: PROFILE });
  });

  it("appelle GET /profile/", async () => {
    const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/profile/");
  });

  it("retourne les données du profil", async () => {
    const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data?.display_name).toBe("Example User");
    expect(result.current.data?.data?.id).toBe("u-1");
  });

  it("démarre en loading", () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });
    expect(result.current.isLoading).toBe(true);
  });

  it("isError sur échec API", async () => {
    mockGet.mockRejectedValue(new Error("Unauthorized"));
    const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useUpdateProfile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPatch.mockResolvedValue({ data: { ...PROFILE, display_name: "Example User Updated" } });
  });

  it("appelle PATCH /profile/ avec les données", async () => {
    const { result } = renderHook(() => useUpdateProfile(), { wrapper: createWrapper() });
    result.current.mutate({ display_name: "Example User Updated" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPatch).toHaveBeenCalledWith("/profile/", { display_name: "Example User Updated" });
  });

  it("peut mettre à jour l'avatar_url", async () => {
    const { result } = renderHook(() => useUpdateProfile(), { wrapper: createWrapper() });
    result.current.mutate({ avatar_url: "https://cdn.example.com/avatar.png" });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockPatch).toHaveBeenCalledWith("/profile/", { avatar_url: "https://cdn.example.com/avatar.png" });
  });

  it("isError sur échec PATCH", async () => {
    mockPatch.mockRejectedValue(new Error("Server error"));
    const { result } = renderHook(() => useUpdateProfile(), { wrapper: createWrapper() });
    result.current.mutate({ display_name: "Fail" });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
