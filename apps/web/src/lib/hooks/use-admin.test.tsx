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
  useAdminUsage,
  useAdminOverview,
  useAdminApiKeysUsage,
  useAdminActivity,
} from "./use-admin";

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

// ─── useAdminUsage ──────────────────────────────────────────────────────────

describe("useAdminUsage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({
      data: { months: [], totals: { total_cost_usd: 0, total_input_tokens: 0, total_output_tokens: 0, total_operations: 0 } },
    });
  });

  it("appelle GET /admin/usage?months=6 par défaut", async () => {
    const { result } = renderHook(() => useAdminUsage(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/admin/usage?months=6");
  });

  it("passe le paramètre months personnalisé", async () => {
    const { result } = renderHook(() => useAdminUsage(3), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/admin/usage?months=3");
  });

  it("retourne les données de stats", async () => {
    mockGet.mockResolvedValue({
      data: {
        months: [{ month: "2026-03", operation: "chat", count: 42, input_tokens: 1000, output_tokens: 500, cost_usd: 0.05 }],
        totals: { total_cost_usd: 0.05, total_input_tokens: 1000, total_output_tokens: 500, total_operations: 42 },
      },
    });
    const { result } = renderHook(() => useAdminUsage(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data?.months?.[0]?.operation).toBe("chat");
    expect(result.current.data?.data?.totals.total_operations).toBe(42);
  });

  it("démarre en loading", () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useAdminUsage(), {
      wrapper: createWrapper(),
    });
    expect(result.current.isLoading).toBe(true);
  });

  it("isError sur échec API", async () => {
    mockGet.mockRejectedValue(new Error("Forbidden"));
    const { result } = renderHook(() => useAdminUsage(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ─── useAdminOverview ───────────────────────────────────────────────────────

describe("useAdminOverview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({
      data: { name: "Acme", plan: "team", member_count: 3, workspace_count: 7, source_count: 42, insight_count: 15, trial_ends_at: null },
    });
  });

  it("appelle GET /admin/overview", async () => {
    const { result } = renderHook(() => useAdminOverview(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/admin/overview");
  });

  it("retourne les données overview", async () => {
    const { result } = renderHook(() => useAdminOverview(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data?.plan).toBe("team");
    expect(result.current.data?.data?.member_count).toBe(3);
    expect(result.current.data?.data?.workspace_count).toBe(7);
  });

  it("isError sur échec API", async () => {
    mockGet.mockRejectedValue(new Error("Forbidden"));
    const { result } = renderHook(() => useAdminOverview(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ─── useAdminApiKeysUsage ───────────────────────────────────────────────────

describe("useAdminApiKeysUsage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: { keys: [] } });
  });

  it("appelle GET /admin/api-keys/usage", async () => {
    const { result } = renderHook(() => useAdminApiKeysUsage(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/admin/api-keys/usage");
  });

  it("retourne la liste des clés", async () => {
    mockGet.mockResolvedValue({
      data: {
        keys: [
          { id: "k-1", name: "CI Key", key_prefix: "xv_live_", is_active: true, rpm_limit: 60, rpd_limit: 1000, last_used_at: "2026-03-19T10:00:00Z", created_at: "2026-01-01T00:00:00Z" },
        ],
      },
    });
    const { result } = renderHook(() => useAdminApiKeysUsage(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data?.keys).toHaveLength(1);
    expect(result.current.data?.data?.keys?.[0]?.name).toBe("CI Key");
  });

  it("retourne liste vide si aucune clé", async () => {
    const { result } = renderHook(() => useAdminApiKeysUsage(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data?.keys).toHaveLength(0);
  });
});

// ─── useAdminActivity ───────────────────────────────────────────────────────

describe("useAdminActivity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: { items: [] } });
  });

  it("appelle GET /admin/activity?limit=50 par défaut", async () => {
    const { result } = renderHook(() => useAdminActivity(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/admin/activity?limit=50");
  });

  it("passe le paramètre limit personnalisé", async () => {
    const { result } = renderHook(() => useAdminActivity(10), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGet).toHaveBeenCalledWith("/admin/activity?limit=10");
  });

  it("retourne les items d'activité", async () => {
    mockGet.mockResolvedValue({
      data: {
        items: [
          { id: "j-1", type: "scan_workspace", status: "completed", created_at: "2026-03-19T10:00:00Z", completed_at: "2026-03-19T10:01:00Z", workspace_name: "ProjectAlpha" },
        ],
      },
    });
    const { result } = renderHook(() => useAdminActivity(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.data?.items).toHaveLength(1);
    expect(result.current.data?.data?.items?.[0]?.type).toBe("scan_workspace");
  });

  it("isError sur échec API", async () => {
    mockGet.mockRejectedValue(new Error("Forbidden"));
    const { result } = renderHook(() => useAdminActivity(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
