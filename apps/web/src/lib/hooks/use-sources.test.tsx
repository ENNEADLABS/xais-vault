import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const mockGet = vi.fn();
const mockUpload = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    upload: (...args: unknown[]) => mockUpload(...args),
    setOrganizationId: vi.fn(),
  },
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: "fake-token" } },
      }),
    },
  }),
}));

vi.mock("@/stores/ui-store", () => ({
  useUIStore: vi.fn((selector: (s: { organizationId: string }) => unknown) =>
    selector({ organizationId: "org-1" }),
  ),
}));

import { useSources, useUploadSource } from "./use-sources";

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

describe("useSources", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: [] });
  });

  it("fetches sources for a workspace", async () => {
    const { result } = renderHook(() => useSources("workspace-1"), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/workspaces/workspace-1/sources/");
  });

  it("is disabled without workspace ID", () => {
    const { result } = renderHook(() => useSources(""), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("returns sources after resolution", async () => {
    const sources = [{ id: "s-1", name: "Report.pdf" }];
    mockGet.mockResolvedValue({ data: sources });
    const { result } = renderHook(() => useSources("workspace-1"), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data).toEqual(sources);
  });

  it("returns error on API failure", async () => {
    mockGet.mockRejectedValue(new Error("fail"));
    const { result } = renderHook(() => useSources("workspace-1"), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useUploadSource", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls api.upload with correct path and FormData", async () => {
    mockUpload.mockResolvedValue({ data: { id: "src-1", name: "test.pdf" } });

    const { result } = renderHook(() => useUploadSource("workspace-1"), {
      wrapper: createWrapper(),
    });

    const file = new File(["content"], "test.pdf", {
      type: "application/pdf",
    });
    await result.current.mutateAsync(file);

    expect(mockUpload).toHaveBeenCalledWith(
      "/workspaces/workspace-1/sources/",
      expect.any(FormData),
    );
    const formData = mockUpload.mock.calls[0]![1] as FormData;
    expect(formData.get("file")).toBe(file);
  });

  it("invalidates sources cache after success", async () => {
    mockUpload.mockResolvedValue({ data: { id: "src-1" } });

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

    const { result } = renderHook(() => useUploadSource("workspace-1"), { wrapper });
    const file = new File(["x"], "doc.pdf", { type: "application/pdf" });
    await result.current.mutateAsync(file);

    expect(spy).toHaveBeenCalledWith({ queryKey: ["sources", "workspace-1"] });
  });

  it("propagates upload error", async () => {
    const error = { error: { code: 413, message: "Too large" } };
    mockUpload.mockRejectedValue(error);

    const { result } = renderHook(() => useUploadSource("workspace-1"), {
      wrapper: createWrapper(),
    });

    const file = new File(["x"], "big.pdf", { type: "application/pdf" });
    await expect(result.current.mutateAsync(file)).rejects.toEqual(error);
  });
});
