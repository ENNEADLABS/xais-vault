import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { SmartPromptsBar, type WorkspaceContext } from "./smart-prompts-bar";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    if (values && "count" in values) return `${values.count} source(s) en cours...`;
    return key;
  },
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

function makeContext(overrides: Partial<WorkspaceContext> = {}): WorkspaceContext {
  return {
    sourceCount: 0,
    processingCount: 0,
    readyCount: 0,
    scanStatus: "pending",
    insightsCount: 0,
    criticalCount: 0,
    investigationCount: 0,
    ...overrides,
  };
}

describe("SmartPromptsBar", () => {
  const mockOnPrompt = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing when no prompts match", () => {
    // sourceCount=0 donne un prompt "howToStart" → devrait rendre qqchose
    // Pour n'avoir aucun prompt, on a besoin de sources sans ready et sans processing
    const ctx = makeContext({ sourceCount: 1, readyCount: 0, processingCount: 0 });
    const { container } = renderWithProviders(
      <SmartPromptsBar context={ctx} onPrompt={mockOnPrompt} />,
    );
    // Pas de source ready, pas de processing, pas de scan, pas de sourceCount=0
    // → aucun prompt ne matche → null
    expect(container.firstChild).toBeNull();
  });

  it("shows 'how to start' when no sources", () => {
    const ctx = makeContext({ sourceCount: 0 });
    renderWithProviders(
      <SmartPromptsBar context={ctx} onPrompt={mockOnPrompt} />,
    );
    expect(screen.getByText("smartPrompts.howToStart")).toBeInTheDocument();
  });

  it("shows processing indicator when sources are indexing", () => {
    const ctx = makeContext({ sourceCount: 3, processingCount: 2 });
    renderWithProviders(
      <SmartPromptsBar context={ctx} onPrompt={mockOnPrompt} />,
    );
    expect(screen.getByText("2 source(s) en cours...")).toBeInTheDocument();
  });

  it("shows red flags + scan summary when scanned with insights", () => {
    const ctx = makeContext({
      sourceCount: 5,
      readyCount: 5,
      scanStatus: "scanned",
      insightsCount: 10,
      criticalCount: 3,
    });
    renderWithProviders(
      <SmartPromptsBar context={ctx} onPrompt={mockOnPrompt} />,
    );
    expect(screen.getByText("smartPrompts.redFlags")).toBeInTheDocument();
    expect(screen.getByText("smartPrompts.scanSummary")).toBeInTheDocument();
  });

  it("shows investigations prompt when investigations exist", () => {
    const ctx = makeContext({
      sourceCount: 5,
      readyCount: 5,
      scanStatus: "scanned",
      insightsCount: 3,
      investigationCount: 2,
    });
    renderWithProviders(
      <SmartPromptsBar context={ctx} onPrompt={mockOnPrompt} />,
    );
    expect(screen.getByText("smartPrompts.investigations")).toBeInTheDocument();
  });

  it("shows metrics + strengths when ready sources exist", () => {
    const ctx = makeContext({ sourceCount: 3, readyCount: 3 });
    renderWithProviders(
      <SmartPromptsBar context={ctx} onPrompt={mockOnPrompt} />,
    );
    expect(screen.getByText("smartPrompts.metrics")).toBeInTheDocument();
    expect(screen.getByText("smartPrompts.strengths")).toBeInTheDocument();
  });

  it("limits to max 4 prompts", () => {
    const ctx = makeContext({
      sourceCount: 5,
      readyCount: 5,
      processingCount: 1,
      scanStatus: "scanned",
      insightsCount: 10,
      investigationCount: 2,
    });
    renderWithProviders(
      <SmartPromptsBar context={ctx} onPrompt={mockOnPrompt} />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeLessThanOrEqual(4);
  });

  it("calls onPrompt when a chip is clicked", () => {
    const ctx = makeContext({ sourceCount: 0 });
    renderWithProviders(
      <SmartPromptsBar context={ctx} onPrompt={mockOnPrompt} />,
    );
    fireEvent.click(screen.getByText("smartPrompts.howToStart"));
    expect(mockOnPrompt).toHaveBeenCalledWith("smartPrompts.howToStartPrompt");
  });

  it("disables chips when disabled prop is true", () => {
    const ctx = makeContext({ sourceCount: 0 });
    renderWithProviders(
      <SmartPromptsBar context={ctx} onPrompt={mockOnPrompt} disabled />,
    );
    const btn = screen.getByText("smartPrompts.howToStart");
    expect(btn.closest("button")).toBeDisabled();
  });

  it("processing chip is disabled", () => {
    const ctx = makeContext({ sourceCount: 3, processingCount: 1, readyCount: 2 });
    renderWithProviders(
      <SmartPromptsBar context={ctx} onPrompt={mockOnPrompt} />,
    );
    const processingBtn = screen.getByText("1 source(s) en cours...");
    expect(processingBtn.closest("button")).toBeDisabled();
  });
});
