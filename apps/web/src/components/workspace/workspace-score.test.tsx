import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { computeWorkspaceScore, WorkspaceScore } from "./workspace-score";
import type { Insight, Investigation, Deliverable } from "@/types/api";

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

// ─── Factories ───────────────────────────────────────────

function makeInsight(overrides: Partial<Insight> = {}): Insight {
  return {
    id: "f-1",
    workspace_id: "workspace-1",
    organization_id: "org-1",
    type: "red_flag",
    severity: "medium",
    confidence_score: 70,
    title: "Test insight",
    description: "Description",
    source_id: null,
    source_name: null,
    source_page: null,
    source_section: null,
    source_quote: null,
    status: "pending",
    reviewed_by: null,
    reviewed_at: null,
    verification: null,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
    ...overrides,
  };
}

function makeInvestigation(overrides: Partial<Investigation> = {}): Investigation {
  return {
    id: "inv-1",
    workspace_id: "workspace-1",
    organization_id: "org-1",
    insight_id: null,
    requested_by: "user-1",
    question: "Question?",
    scope: "documents",
    status: "pending",
    report: null,
    web_sources: null,
    doc_references: null,
    created_at: "2025-01-01T00:00:00Z",
    started_at: null,
    completed_at: null,
    ...overrides,
  };
}

function makeDeliverable(overrides: Partial<Deliverable> = {}): Deliverable {
  return {
    id: "del-1",
    workspace_id: "workspace-1",
    organization_id: "org-1",
    generated_by: "user-1",
    type: "dd_report",
    name: "DD Report",
    status: "pending",
    content_markdown: null,
    file_path: null,
    file_size_bytes: null,
    options: {},
    current_step: null,
    progress_percent: 0,
    error_message: null,
    created_at: "2025-01-01T00:00:00Z",
    completed_at: null,
    ...overrides,
  };
}

// ─── computeWorkspaceScore ────────────────────────────────────

describe("computeWorkspaceScore", () => {
  it("returns base score 70 with no data", () => {
    expect(computeWorkspaceScore([], [], [])).toBe(70);
  });

  it("penalizes unresolved critical insights (-8 each)", () => {
    const insights = [
      makeInsight({ severity: "critical", status: "pending" }),
      makeInsight({ id: "f-2", severity: "critical", status: "pending" }),
    ];
    // 70 - 16 = 54, + treated bonus 0/2*15 = 0
    expect(computeWorkspaceScore(insights, [], [])).toBe(54);
  });

  it("penalizes unresolved high insights (-4 each)", () => {
    const insights = [
      makeInsight({ severity: "high", status: "pending" }),
    ];
    // 70 - 4 = 66, + 0/1*15 = 0
    expect(computeWorkspaceScore(insights, [], [])).toBe(66);
  });

  it("penalizes unresolved medium insights (-2 each)", () => {
    const insights = [
      makeInsight({ severity: "medium", status: "pending" }),
    ];
    // 70 - 2 = 68
    expect(computeWorkspaceScore(insights, [], [])).toBe(68);
  });

  it("gives bonus for treated insights (confirmed/rejected)", () => {
    const insights = [
      makeInsight({ status: "confirmed" }),
      makeInsight({ id: "f-2", status: "rejected" }),
    ];
    // 70 + (2/2)*15 = 85
    expect(computeWorkspaceScore(insights, [], [])).toBe(85);
  });

  it("gives bonus for completed investigations (max +10)", () => {
    const investigations = Array.from({ length: 5 }, (_, i) =>
      makeInvestigation({ id: `inv-${i}`, status: "completed" }),
    );
    // 70 + min(5*3, 10) = 80
    expect(computeWorkspaceScore([], investigations, [])).toBe(80);
  });

  it("caps investigation bonus at 10", () => {
    const investigations = Array.from({ length: 10 }, (_, i) =>
      makeInvestigation({ id: `inv-${i}`, status: "completed" }),
    );
    // 70 + 10 = 80
    expect(computeWorkspaceScore([], investigations, [])).toBe(80);
  });

  it("gives bonus for completed deliverables (max +5)", () => {
    const deliverables = [
      makeDeliverable({ status: "completed" }),
      makeDeliverable({ id: "del-2", status: "completed" }),
      makeDeliverable({ id: "del-3", status: "completed" }),
    ];
    // 70 + min(3*2, 5) = 75
    expect(computeWorkspaceScore([], [], deliverables)).toBe(75);
  });

  it("clamps score to 0-100 range", () => {
    // Beaucoup de criticals non résolus
    const insights = Array.from({ length: 15 }, (_, i) =>
      makeInsight({ id: `f-${i}`, severity: "critical", status: "pending" }),
    );
    // 70 - 120 = -50, clamped to 0
    expect(computeWorkspaceScore(insights, [], [])).toBe(0);
  });

  it("clamps score max to 100", () => {
    const insights = Array.from({ length: 10 }, (_, i) =>
      makeInsight({ id: `f-${i}`, status: "confirmed" }),
    );
    const investigations = Array.from({ length: 10 }, (_, i) =>
      makeInvestigation({ id: `inv-${i}`, status: "completed" }),
    );
    const deliverables = Array.from({ length: 5 }, (_, i) =>
      makeDeliverable({ id: `del-${i}`, status: "completed" }),
    );
    // 70 + 15 + 10 + 5 = 100
    expect(computeWorkspaceScore(insights, investigations, deliverables)).toBe(100);
  });

  it("ignores pending investigations and deliverables", () => {
    const investigations = [makeInvestigation({ status: "pending" })];
    const deliverables = [makeDeliverable({ status: "pending" })];
    expect(computeWorkspaceScore([], investigations, deliverables)).toBe(70);
  });
});

// ─── WorkspaceScore composant ─────────────────────────────────

describe("WorkspaceScore", () => {
  it("renders score value in SVG text", () => {
    renderWithProviders(
      <WorkspaceScore insights={[]} investigations={[]} deliverables={[]} size="lg" />,
    );
    expect(screen.getByText("70")).toBeInTheDocument();
  });

  it("renders 'Favorable' label for score >= 60", () => {
    renderWithProviders(
      <WorkspaceScore insights={[]} investigations={[]} deliverables={[]} size="lg" />,
    );
    expect(screen.getByText(/Favorable/)).toBeInTheDocument();
  });

  it("renders 'Modéré' label for score 40-59", () => {
    const insights = [
      makeInsight({ severity: "critical", status: "pending" }),
      makeInsight({ id: "f-2", severity: "critical", status: "pending" }),
      makeInsight({ id: "f-3", severity: "high", status: "pending" }),
    ];
    // 70 - 16 - 4 = 50 + 0/3*15 = 50
    renderWithProviders(
      <WorkspaceScore insights={insights} investigations={[]} deliverables={[]} size="lg" />,
    );
    expect(screen.getByText(/Modéré/)).toBeInTheDocument();
  });

  it("renders 'Risqué' label for score < 40", () => {
    const insights = Array.from({ length: 6 }, (_, i) =>
      makeInsight({ id: `f-${i}`, severity: "critical", status: "pending" }),
    );
    // 70 - 48 = 22
    renderWithProviders(
      <WorkspaceScore insights={insights} investigations={[]} deliverables={[]} size="lg" />,
    );
    expect(screen.getByText(/Risqué/)).toBeInTheDocument();
  });

  it("renders small variant without label text", () => {
    renderWithProviders(
      <WorkspaceScore insights={[]} investigations={[]} deliverables={[]} size="sm" />,
    );
    expect(screen.getByText("70")).toBeInTheDocument();
    expect(screen.queryByText(/Favorable/)).not.toBeInTheDocument();
  });

  it("shows unresolved alerts count", () => {
    const insights = [
      makeInsight({ severity: "critical", status: "pending" }),
      makeInsight({ id: "f-2", severity: "high", status: "pending" }),
    ];
    renderWithProviders(
      <WorkspaceScore insights={insights} investigations={[]} deliverables={[]} size="lg" />,
    );
    expect(screen.getByText(/2 alertes non résolues/)).toBeInTheDocument();
  });

  it("shows treated insights count", () => {
    const insights = [
      makeInsight({ status: "confirmed" }),
      makeInsight({ id: "f-2", status: "rejected" }),
      makeInsight({ id: "f-3", status: "pending" }),
    ];
    renderWithProviders(
      <WorkspaceScore insights={insights} investigations={[]} deliverables={[]} size="lg" />,
    );
    expect(screen.getByText(/2 points clés traités sur 3/)).toBeInTheDocument();
  });
});
