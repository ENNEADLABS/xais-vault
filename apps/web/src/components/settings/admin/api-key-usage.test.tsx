import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { mockQueryLoading, mockQuerySuccess } from "@/tests/mocks/query-result";
import { ApiKeyUsage } from "./api-key-usage";
import type { ApiResponse } from "@/lib/api";
import type { ApiKeyUsageItem, ApiKeysUsageResponse } from "@/types/api";

type ApiKeysResult = ApiResponse<ApiKeysUsageResponse>;

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

vi.mock("@/lib/hooks/use-admin", () => ({
  useAdminApiKeysUsage: vi.fn(),
}));

import { useAdminApiKeysUsage } from "@/lib/hooks/use-admin";
const mockUseAdminApiKeysUsage = vi.mocked(useAdminApiKeysUsage);

const API_KEYS: ApiKeyUsageItem[] = [
  {
    id: "key-1",
    name: "Production Key",
    key_prefix: "xv_prod",
    rpm_limit: 60,
    rpd_limit: 10000,
    last_used_at: "2026-03-20T10:00:00Z",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "key-2",
    name: "Dev Key",
    key_prefix: "xv_dev",
    rpm_limit: 30,
    rpd_limit: 5000,
    last_used_at: null,
    is_active: false,
    created_at: "2026-01-01T00:00:00Z",
  },
];

describe("ApiKeyUsage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche les skeletons en loading", () => {
    mockUseAdminApiKeysUsage.mockReturnValue(mockQueryLoading<ApiKeysResult>());

    const { container } = renderWithProviders(<ApiKeyUsage />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(3);
  });

  it("affiche le message vide quand pas de clés", () => {
    mockUseAdminApiKeysUsage.mockReturnValue(mockQuerySuccess<ApiKeysResult>({ data: { keys: [] } }));

    renderWithProviders(<ApiKeyUsage />);
    expect(screen.getByText("noApiKeys")).toBeInTheDocument();
  });

  it("affiche les en-têtes de colonnes", () => {
    mockUseAdminApiKeysUsage.mockReturnValue(mockQuerySuccess<ApiKeysResult>({ data: { keys: API_KEYS } }));

    renderWithProviders(<ApiKeyUsage />);
    expect(screen.getByText("keyName")).toBeInTheDocument();
    expect(screen.getByText("prefix")).toBeInTheDocument();
    expect(screen.getByText("RPM")).toBeInTheDocument();
    expect(screen.getByText("RPD")).toBeInTheDocument();
    expect(screen.getByText("lastUsed")).toBeInTheDocument();
    expect(screen.getByText("keyStatus")).toBeInTheDocument();
  });

  it("affiche les données des clés API", () => {
    mockUseAdminApiKeysUsage.mockReturnValue(mockQuerySuccess<ApiKeysResult>({ data: { keys: API_KEYS } }));

    renderWithProviders(<ApiKeyUsage />);
    expect(screen.getByText("Production Key")).toBeInTheDocument();
    expect(screen.getByText("Dev Key")).toBeInTheDocument();
    expect(screen.getByText("xv_prod…")).toBeInTheDocument();
    expect(screen.getByText("xv_dev…")).toBeInTheDocument();
    expect(screen.getByText("60")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
  });

  it("affiche le statut actif/inactif", () => {
    mockUseAdminApiKeysUsage.mockReturnValue(mockQuerySuccess<ApiKeysResult>({ data: { keys: API_KEYS } }));

    renderWithProviders(<ApiKeyUsage />);
    expect(screen.getByText("active")).toBeInTheDocument();
    expect(screen.getByText("inactive")).toBeInTheDocument();
  });

  it("affiche un tiret quand last_used_at est null", () => {
    mockUseAdminApiKeysUsage.mockReturnValue(mockQuerySuccess<ApiKeysResult>({ data: { keys: API_KEYS } }));

    renderWithProviders(<ApiKeyUsage />);
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });
});
