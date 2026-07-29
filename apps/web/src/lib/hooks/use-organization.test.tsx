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

// next-intl navigation utilisé dans useLeaveOrganization / useDeleteOrganization
vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Zustand ui-store — on n'a pas besoin de la logique réelle ici
vi.mock("@/stores/ui-store", () => ({
  useUIStore: () => vi.fn(),
}));

import { useCurrentOrgRole } from "./use-organization";

const ORG_ID = "org-test-123";
const USER_ID = "user-abc";

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

/** Configure mockGet pour retourner profil + membres selon l'URL appelée. */
function setupMocks(userId: string, members: { user_id: string; role: string }[]) {
  mockGet.mockImplementation((url: string) => {
    if (url === "/profile/") {
      return Promise.resolve({ data: { id: userId, display_name: "Example User" } });
    }
    if (url.includes("/members")) {
      return Promise.resolve({ data: members });
    }
    return Promise.resolve({ data: null });
  });
}

describe("useCurrentOrgRole", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("retourne null pendant le chargement", () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useCurrentOrgRole(ORG_ID), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBeNull();
  });

  it("retourne 'admin' quand l'utilisateur est admin", async () => {
    setupMocks(USER_ID, [
      { user_id: USER_ID, role: "admin" },
      { user_id: "other-user", role: "analyst" },
    ]);
    const { result } = renderHook(() => useCurrentOrgRole(ORG_ID), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current).not.toBeNull());
    expect(result.current).toBe("admin");
  });

  it("retourne 'analyst' quand l'utilisateur est analyst", async () => {
    setupMocks(USER_ID, [
      { user_id: "admin-user", role: "admin" },
      { user_id: USER_ID, role: "analyst" },
    ]);
    const { result } = renderHook(() => useCurrentOrgRole(ORG_ID), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current).not.toBeNull());
    expect(result.current).toBe("analyst");
  });

  it("retourne 'viewer' quand l'utilisateur est viewer", async () => {
    setupMocks(USER_ID, [{ user_id: USER_ID, role: "viewer" }]);
    const { result } = renderHook(() => useCurrentOrgRole(ORG_ID), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current).not.toBeNull());
    expect(result.current).toBe("viewer");
  });

  it("retourne null quand l'utilisateur n'est pas membre de l'org", async () => {
    setupMocks(USER_ID, [
      { user_id: "somebody-else", role: "admin" },
    ]);
    const { result } = renderHook(() => useCurrentOrgRole(ORG_ID), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    // Attendre que les queries se résolvent
    await waitFor(() => {
      // les deux queries doivent avoir été appelées
      expect(mockGet).toHaveBeenCalledWith("/profile/");
    });
    await waitFor(() => expect(result.current).toBeNull());
  });

  it("retourne null quand la liste des membres est vide", async () => {
    setupMocks(USER_ID, []);
    const { result } = renderHook(() => useCurrentOrgRole(ORG_ID), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    await waitFor(() => expect(result.current).toBeNull());
  });

  it("retourne null quand le profil n'a pas d'id", async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === "/profile/") return Promise.resolve({ data: null });
      if (url.includes("/members")) return Promise.resolve({ data: [{ user_id: USER_ID, role: "admin" }] });
      return Promise.resolve({ data: null });
    });
    const { result } = renderHook(() => useCurrentOrgRole(ORG_ID), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    await waitFor(() => expect(result.current).toBeNull());
  });
});
