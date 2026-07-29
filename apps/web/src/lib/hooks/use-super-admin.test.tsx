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

import {
  useSuperAdminCheck,
  usePlatformOverview,
  useOrgMetrics,
  useUserActivity,
  useGlobalActivity,
  useErrorLog,
} from "./use-super-admin";

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe("useSuperAdminCheck", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ is_super_admin: true });
  });

  it("appelle GET /super-admin/check", async () => {
    const { result } = renderHook(() => useSuperAdminCheck(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/super-admin/check");
    expect(result.current.data?.is_super_admin).toBe(true);
  });
});

describe("usePlatformOverview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({
      total_organizations: 5,
      total_workspaces: 42,
      active_orgs_7d: 3,
      job_success_rate_7d: 95.5,
    });
  });

  it("appelle GET /super-admin/overview", async () => {
    const { result } = renderHook(() => usePlatformOverview(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/super-admin/overview");
    expect(result.current.data?.total_workspaces).toBe(42);
  });
});

describe("useOrgMetrics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue([
      { org_id: "1", org_name: "Acme", workspace_count: 7 },
    ]);
  });

  it("appelle GET /super-admin/organizations", async () => {
    const { result } = renderHook(() => useOrgMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/super-admin/organizations");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((result.current.data as any)[0].org_name).toBe("Acme");
  });
});

describe("useUserActivity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue([]);
  });

  it("appelle sans filtre par défaut", async () => {
    const { result } = renderHook(() => useUserActivity(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/super-admin/users");
  });

  it("appelle avec filtre org_id", async () => {
    const { result } = renderHook(() => useUserActivity("org-123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/super-admin/users?org_id=org-123");
  });
});

describe("useGlobalActivity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue([
      { id: "1", type: "scan_workspace", status: "completed" },
    ]);
  });

  it("appelle GET /super-admin/activity avec limit", async () => {
    const { result } = renderHook(() => useGlobalActivity(50), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/super-admin/activity?limit=50");
  });
});

describe("useErrorLog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue([]);
  });

  it("appelle GET /super-admin/errors avec limit", async () => {
    const { result } = renderHook(() => useErrorLog(25), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/super-admin/errors?limit=25");
  });
});
