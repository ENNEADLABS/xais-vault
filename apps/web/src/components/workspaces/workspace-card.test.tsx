import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { WorkspaceCard } from "./workspace-card";
import type { Workspace } from "@/types/api";

const mockPush = vi.fn();

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  Link: ({ href, children, ...props }: { href: string; children: React.ReactNode; [key: string]: unknown }) => {
    return <a href={href} onClick={() => mockPush(href)} {...props}>{children}</a>;
  },
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, unknown>) => {
    if (params?.count !== undefined) return `${key}: ${params.count}`;
    return key;
  },
  useLocale: () => "fr",
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
  formatRelativeDate: () => "il y a 2j",
}));

const WORKSPACE: Workspace = {
  id: "workspace-1",
  name: "Acme Corp",
  emoji: "🚀",
  description: "Test workspace",
  deal_type: "equity",
  sector: "tech",
  target_company: "Acme SAS",
  status: "active",
  scan_status: "pending",
  organization_id: "org-1",
  created_by: "user-1",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
  source_count: 5,
  insight_count: 3,
};

describe("WorkspaceCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders workspace name", () => {
    renderWithProviders(<WorkspaceCard workspace={WORKSPACE} />);
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
  });

  it("renders emoji", () => {
    renderWithProviders(<WorkspaceCard workspace={WORKSPACE} />);
    expect(screen.getByText("🚀")).toBeInTheDocument();
  });

  it("renders target company", () => {
    renderWithProviders(<WorkspaceCard workspace={WORKSPACE} />);
    expect(screen.getByText("Acme SAS")).toBeInTheDocument();
  });

  it("active workspaces have no visible status badge text", () => {
    renderWithProviders(<WorkspaceCard workspace={WORKSPACE} />);
    // Active workspaces use border-l accent, no badge label rendered
    expect(screen.queryByText("statusActive")).not.toBeInTheDocument();
    expect(screen.queryByText("statusArchived")).not.toBeInTheDocument();
  });

  it("does not render target_company when null", () => {
    const workspace = { ...WORKSPACE, target_company: null };
    renderWithProviders(<WorkspaceCard workspace={workspace} />);
    expect(screen.queryByText("Acme SAS")).not.toBeInTheDocument();
  });

  it("renders scan status tag", () => {
    renderWithProviders(<WorkspaceCard workspace={WORKSPACE} />);
    // Le redesign affiche un tag monospace [PENDING] avec le label traduit en title
    expect(screen.getByText("[PENDING]")).toBeInTheDocument();
    expect(screen.getByTitle("scanPending")).toBeInTheDocument();
  });

  it("renders source and insight counts", () => {
    renderWithProviders(<WorkspaceCard workspace={WORKSPACE} />);
    expect(screen.getByText("sources: 5")).toBeInTheDocument();
    expect(screen.getByText("insights: 3")).toBeInTheDocument();
  });

  it("navigates on click", () => {
    renderWithProviders(<WorkspaceCard workspace={WORKSPACE} />);
    const links = screen.getAllByRole("link");
    const firstLink = links[0]!;
    expect(firstLink).toHaveAttribute("href", "/workspaces/workspace-1");
    fireEvent.click(firstLink);
    expect(mockPush).toHaveBeenCalledWith("/workspaces/workspace-1");
  });
});
