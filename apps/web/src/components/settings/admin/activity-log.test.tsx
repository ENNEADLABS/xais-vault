import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { mockQueryLoading, mockQuerySuccess } from "@/tests/mocks/query-result";
import { ActivityLog } from "./activity-log";
import type { ApiResponse } from "@/lib/api";
import type { ActivityItem, ActivityLogResponse } from "@/types/api";

type ActivityResult = ApiResponse<ActivityLogResponse>;

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

vi.mock("@/lib/hooks/use-admin", () => ({
  useAdminActivity: vi.fn(),
}));

import { useAdminActivity } from "@/lib/hooks/use-admin";
const mockUseAdminActivity = vi.mocked(useAdminActivity);

const ACTIVITY_ITEMS: ActivityItem[] = [
  {
    id: "job-1",
    type: "scan_workspace",
    status: "completed",
    workspace_name: "Acme Corp",
    source_name: null,
    completed_at: "2026-03-20T10:30:05Z",
    created_at: "2026-03-20T10:30:00Z",
  },
  {
    id: "job-2",
    type: "index_source",
    status: "failed",
    workspace_name: null,
    source_name: "rapport.pdf",
    completed_at: null,
    created_at: "2026-03-20T09:15:00Z",
  },
  {
    id: "job-3",
    type: "generate_deliverable",
    status: "processing",
    workspace_name: null,
    source_name: null,
    completed_at: null,
    created_at: "2026-03-20T08:00:00Z",
  },
];

describe("ActivityLog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche les skeletons en loading", () => {
    mockUseAdminActivity.mockReturnValue(mockQueryLoading<ActivityResult>());

    const { container } = renderWithProviders(<ActivityLog />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(6);
  });

  it("affiche le message vide quand pas d'activité", () => {
    mockUseAdminActivity.mockReturnValue(mockQuerySuccess<ActivityResult>({ data: { items: [] } }));

    renderWithProviders(<ActivityLog />);
    expect(screen.getByText("noActivity")).toBeInTheDocument();
  });

  it("affiche les en-têtes de colonnes", () => {
    mockUseAdminActivity.mockReturnValue(mockQuerySuccess<ActivityResult>({ data: { items: ACTIVITY_ITEMS } }));

    renderWithProviders(<ActivityLog />);
    expect(screen.getByText("jobType")).toBeInTheDocument();
    expect(screen.getByText("workspace")).toBeInTheDocument();
    expect(screen.getByText("status")).toBeInTheDocument();
    expect(screen.getByText("date")).toBeInTheDocument();
  });

  it("affiche les labels traduits pour les types de job", () => {
    mockUseAdminActivity.mockReturnValue(mockQuerySuccess<ActivityResult>({ data: { items: ACTIVITY_ITEMS } }));

    renderWithProviders(<ActivityLog />);
    expect(screen.getByText("Scan")).toBeInTheDocument();
    expect(screen.getByText("Indexation")).toBeInTheDocument();
    expect(screen.getByText("Livrable")).toBeInTheDocument();
  });

  it("affiche workspace_name ou source_name ou tiret", () => {
    mockUseAdminActivity.mockReturnValue(mockQuerySuccess<ActivityResult>({ data: { items: ACTIVITY_ITEMS } }));

    renderWithProviders(<ActivityLog />);
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("rapport.pdf")).toBeInTheDocument();
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it("affiche les badges de statut", () => {
    mockUseAdminActivity.mockReturnValue(mockQuerySuccess<ActivityResult>({ data: { items: ACTIVITY_ITEMS } }));

    renderWithProviders(<ActivityLog />);
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
    expect(screen.getByText("processing")).toBeInTheDocument();
  });
});
