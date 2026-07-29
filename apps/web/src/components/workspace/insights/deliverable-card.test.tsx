import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { DeliverableCard } from "./deliverable-card";
import type { Deliverable } from "@/types/api";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
  useLocale: () => "fr",
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
  formatFileSize: (bytes: number) => `${bytes} B`,
  formatRelativeDate: () => "il y a 1h",
}));

vi.mock("@/lib/api", () => ({
  API_URL: "http://localhost:8000",
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getSession: () =>
        Promise.resolve({ data: { session: { access_token: "test-jwt" } } }),
    },
  }),
}));

vi.mock("react-markdown", () => ({
  default: ({ children }: { children: string }) => <div data-testid="markdown">{children}</div>,
}));

vi.mock("remark-gfm", () => ({
  default: () => null,
}));

function makeDeliverable(overrides: Partial<Deliverable> = {}): Deliverable {
  return {
    id: "del-1",
    workspace_id: "workspace-1",
    organization_id: "org-1",
    generated_by: "user-1",
    type: "dd_report",
    name: "DD Report TechCorp",
    status: "completed",
    content_markdown: "# Rapport\n\nContenu du rapport.",
    file_path: "/path/to/file.docx",
    file_size_bytes: 15000,
    options: {},
    current_step: null,
    progress_percent: 100,
    error_message: null,
    created_at: "2025-01-01T00:00:00Z",
    completed_at: "2025-01-01T12:00:00Z",
    ...overrides,
  };
}

describe("DeliverableCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders deliverable name", () => {
    renderWithProviders(<DeliverableCard deliverable={makeDeliverable()} />);
    expect(screen.getByText("DD Report TechCorp")).toBeInTheDocument();
  });

  it("renders type badge", () => {
    renderWithProviders(<DeliverableCard deliverable={makeDeliverable()} />);
    expect(screen.getByText("DD Report")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    renderWithProviders(<DeliverableCard deliverable={makeDeliverable()} />);
    expect(screen.getByText("statusCompleted")).toBeInTheDocument();
  });

  it("shows download button when completed", () => {
    renderWithProviders(<DeliverableCard deliverable={makeDeliverable()} />);
    expect(screen.getByText("download")).toBeInTheDocument();
  });

  it("shows preview button when content_markdown is available", () => {
    renderWithProviders(<DeliverableCard deliverable={makeDeliverable()} />);
    expect(screen.getByText("preview")).toBeInTheDocument();
  });

  it("does not show preview button when content_markdown is null", () => {
    renderWithProviders(
      <DeliverableCard deliverable={makeDeliverable({ content_markdown: null })} />,
    );
    expect(screen.queryByText("preview")).not.toBeInTheDocument();
  });

  it("shows markdown content when preview is clicked", () => {
    renderWithProviders(<DeliverableCard deliverable={makeDeliverable()} />);

    fireEvent.click(screen.getByText("preview"));

    expect(screen.getByTestId("markdown")).toBeInTheDocument();
    expect(screen.getByText(/Contenu du rapport/)).toBeInTheDocument();
  });

  it("hides markdown when preview is toggled off", () => {
    renderWithProviders(<DeliverableCard deliverable={makeDeliverable()} />);

    // Ouvrir
    fireEvent.click(screen.getByText("preview"));
    expect(screen.getByTestId("markdown")).toBeInTheDocument();

    // Fermer
    fireEvent.click(screen.getByText("closePreview"));
    expect(screen.queryByTestId("markdown")).not.toBeInTheDocument();
  });

  it("shows progress bar when processing", () => {
    renderWithProviders(
      <DeliverableCard
        deliverable={makeDeliverable({
          status: "processing",
          progress_percent: 45,
          current_step: "Analyse insights",
        })}
      />,
    );
    expect(screen.getByText("45%")).toBeInTheDocument();
  });

  it("shows error message when failed", () => {
    renderWithProviders(
      <DeliverableCard
        deliverable={makeDeliverable({
          status: "failed",
          error_message: "LLM timeout",
        })}
      />,
    );
    expect(screen.getByText("LLM timeout")).toBeInTheDocument();
  });
});
