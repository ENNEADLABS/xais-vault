import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { MessageList } from "./message-list";
import type { WorkspaceContext } from "../smart-prompts-bar";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    if (key === "emptyStateContext" && values)
      return `${values.sources} sources · ${values.pages} pages indexées`;
    return key;
  },
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

// Mock des stores utilisés par CitationBadge/MessageBubble
vi.mock("@/stores/workspace-interaction-store", () => ({
  useWorkspaceInteractionStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({
      setHighlightSource: vi.fn(),
      setScrollToSourceId: vi.fn(),
    }),
}));

vi.mock("@/stores/panel-store", () => ({
  usePanelStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({
      leftCollapsed: false,
      toggleLeft: vi.fn(),
    }),
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

describe("MessageList — empty state contextuel", () => {
  const mockSuggestionClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows upload message when no sources", () => {
    renderWithProviders(
      <MessageList
        messages={[]}
        isLoading={false}
        isStreaming={false}
        streamingText=""
        streamingCitations={[]}
        dealContext={makeContext({ sourceCount: 0, readyCount: 0 })}
      />,
    );
    expect(screen.getByText("emptyStateNoSources")).toBeInTheDocument();
  });

  it("shows ready state with source and page count", () => {
    renderWithProviders(
      <MessageList
        messages={[]}
        isLoading={false}
        isStreaming={false}
        streamingText=""
        streamingCitations={[]}
        onSuggestionClick={mockSuggestionClick}
        dealContext={makeContext({ sourceCount: 8, readyCount: 8 })}
        totalPages={156}
      />,
    );
    expect(screen.getByText("emptyStateReady")).toBeInTheDocument();
    expect(
      screen.getByText("8 sources · 156 pages indexées"),
    ).toBeInTheDocument();
    expect(screen.getByText("emptyStateHint")).toBeInTheDocument();
  });

  it("shows suggestion buttons when ready sources exist", () => {
    renderWithProviders(
      <MessageList
        messages={[]}
        isLoading={false}
        isStreaming={false}
        streamingText=""
        streamingCitations={[]}
        onSuggestionClick={mockSuggestionClick}
        dealContext={makeContext({ sourceCount: 5, readyCount: 5 })}
      />,
    );
    // Les 3 suggestions: redFlags, financials, risks
    expect(screen.getByText("suggestions.redFlags")).toBeInTheDocument();
    expect(screen.getByText("suggestions.financials")).toBeInTheDocument();
    expect(screen.getByText("suggestions.risks")).toBeInTheDocument();
  });

  it("does not show suggestion buttons when no ready sources", () => {
    renderWithProviders(
      <MessageList
        messages={[]}
        isLoading={false}
        isStreaming={false}
        streamingText=""
        streamingCitations={[]}
        onSuggestionClick={mockSuggestionClick}
        dealContext={makeContext({ sourceCount: 0, readyCount: 0 })}
      />,
    );
    expect(screen.queryByText("suggestions.redFlags")).not.toBeInTheDocument();
  });

  it("calls onSuggestionClick when a suggestion is clicked", () => {
    renderWithProviders(
      <MessageList
        messages={[]}
        isLoading={false}
        isStreaming={false}
        streamingText=""
        streamingCitations={[]}
        onSuggestionClick={mockSuggestionClick}
        dealContext={makeContext({ sourceCount: 3, readyCount: 3 })}
      />,
    );
    fireEvent.click(screen.getByText("suggestions.redFlags"));
    expect(mockSuggestionClick).toHaveBeenCalledWith("suggestions.redFlags");
  });

  it("shows loading skeleton when isLoading", () => {
    const { container } = renderWithProviders(
      <MessageList
        messages={[]}
        isLoading
        isStreaming={false}
        streamingText=""
        streamingCitations={[]}
      />,
    );
    // Les Skeleton sont des divs avec role="status"
    expect(container.querySelector("[aria-busy='true']")).toBeInTheDocument();
  });
});
