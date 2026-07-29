import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { buildTimeline, ActivityTimeline } from "./activity-timeline";
import type { Source, Insight, Investigation, Deliverable, Note } from "@/types/api";

vi.mock("next-intl", () => ({
  useLocale: () => "fr",
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
  formatRelativeDate: (date: string) => {
    // Retourne une date simplifiée pour les tests
    return new Date(date).toISOString().slice(0, 10);
  },
}));

// ─── Factories ───────────────────────────────────────────

function makeSource(overrides: Partial<Source> = {}): Source {
  return {
    id: "src-1",
    workspace_id: "workspace-1",
    organization_id: "org-1",
    name: "Document.pdf",
    type: "pdf",
    file_size_bytes: 1000,
    status: "ready",
    error_message: null,
    page_count: 10,
    word_count: 5000,
    summary: null,
    topics: null,
    suggested_questions: null,
    created_at: "2025-01-03T00:00:00Z",
    updated_at: "2025-01-03T00:00:00Z",
    ...overrides,
  };
}

function makeInsight(overrides: Partial<Insight> = {}): Insight {
  return {
    id: "f-1",
    workspace_id: "workspace-1",
    organization_id: "org-1",
    type: "red_flag",
    severity: "high",
    confidence_score: 70,
    title: "Test insight",
    description: "Desc",
    source_id: null,
    source_name: null,
    source_page: null,
    source_section: null,
    source_quote: null,
    status: "confirmed",
    reviewed_by: null,
    reviewed_at: null,
    verification: null,
    created_at: "2025-01-02T00:00:00Z",
    updated_at: "2025-01-02T00:00:00Z",
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
    question: "Market size?",
    scope: "both",
    status: "completed",
    report: "Report content",
    web_sources: null,
    doc_references: null,
    created_at: "2025-01-01T00:00:00Z",
    started_at: "2025-01-01T01:00:00Z",
    completed_at: "2025-01-01T02:00:00Z",
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
    status: "completed",
    content_markdown: null,
    file_path: null,
    file_size_bytes: null,
    options: {},
    current_step: null,
    progress_percent: 100,
    error_message: null,
    created_at: "2025-01-04T00:00:00Z",
    completed_at: "2025-01-04T12:00:00Z",
    ...overrides,
  };
}

function makeNote(overrides: Partial<Note> = {}): Note {
  return {
    id: "note-1",
    workspace_id: "workspace-1",
    user_id: "user-1",
    title: "Ma note",
    content: "Contenu",
    tags: [],
    is_pinned: false,
    checklist_items: null,
    linked_source_id: null,
    linked_insight_id: null,
    linked_message_id: null,
    created_at: "2025-01-05T00:00:00Z",
    updated_at: "2025-01-05T00:00:00Z",
    ...overrides,
  };
}

// ─── buildTimeline ───────────────────────────────────────

describe("buildTimeline", () => {
  it("returns empty array with no data", () => {
    expect(buildTimeline([], [], [], [], [])).toEqual([]);
  });

  it("sorts events by date descending", () => {
    const events = buildTimeline(
      [makeSource({ created_at: "2025-01-01T00:00:00Z" })],
      [makeInsight({ updated_at: "2025-01-03T00:00:00Z" })],
      [makeInvestigation({ completed_at: "2025-01-02T00:00:00Z" })],
      [],
      [],
    );
    expect(events[0]?.type).toBe("insight");
    expect(events[1]?.type).toBe("investigation");
    expect(events[2]?.type).toBe("source");
  });

  it("maps source status to label", () => {
    const events = buildTimeline(
      [makeSource({ name: "Doc.pdf", status: "ready" })],
      [], [], [], [],
    );
    expect(events[0]?.title).toContain("indexé");
  });

  it("maps insight status to label", () => {
    const events = buildTimeline(
      [],
      [makeInsight({ title: "Red Flag", status: "confirmed" })],
      [], [], [],
    );
    expect(events[0]?.title).toContain("confirmé");
  });

  it("maps investigation status to label", () => {
    const events = buildTimeline(
      [], [],
      [makeInvestigation({ question: "Taille de marché", status: "completed" })],
      [], [],
    );
    expect(events[0]?.title).toContain("terminée");
  });

  it("truncates long investigation questions", () => {
    const longQ = "A".repeat(80);
    const events = buildTimeline(
      [], [],
      [makeInvestigation({ question: longQ })],
      [], [],
    );
    expect(events[0]?.title).toContain("…");
  });

  it("includes all entity types", () => {
    const events = buildTimeline(
      [makeSource()],
      [makeInsight()],
      [makeInvestigation()],
      [makeDeliverable()],
      [makeNote()],
    );
    const types = events.map((e) => e.type);
    expect(types).toContain("source");
    expect(types).toContain("insight");
    expect(types).toContain("investigation");
    expect(types).toContain("deliverable");
    expect(types).toContain("note");
  });
});

// ─── ActivityTimeline composant ──────────────────────────

describe("ActivityTimeline", () => {
  it("renders events", () => {
    renderWithProviders(
      <ActivityTimeline
        sources={[makeSource({ name: "Business_Plan.pdf" })]}
        insights={[]}
        investigations={[]}
        deliverables={[]}
        notes={[]}
      />,
    );
    expect(screen.getByText(/Business_Plan\.pdf/)).toBeInTheDocument();
  });

  it("limits displayed events to maxItems", () => {
    const sources = Array.from({ length: 10 }, (_, i) =>
      makeSource({ id: `src-${i}`, name: `Doc${i}.pdf` }),
    );
    renderWithProviders(
      <ActivityTimeline
        sources={sources}
        insights={[]}
        investigations={[]}
        deliverables={[]}
        notes={[]}
        maxItems={3}
      />,
    );
    // Chaque event a un texte avec le nom du doc
    const items = screen.getAllByText(/Doc\d+\.pdf/);
    expect(items).toHaveLength(3);
  });

  it("returns null when no events", () => {
    const { container } = renderWithProviders(
      <ActivityTimeline
        sources={[]}
        insights={[]}
        investigations={[]}
        deliverables={[]}
        notes={[]}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});
