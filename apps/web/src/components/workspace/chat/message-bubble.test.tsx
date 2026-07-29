import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { MessageBubble } from "./message-bubble";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

// Mock des stores utilisés par CitationBadge (importé par MessageBubble)
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

describe("MessageBubble", () => {
  const mockOnFeedback = vi.fn();
  const mockOnSaveAsNote = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders user message", () => {
    renderWithProviders(
      <MessageBubble role="user" content="Bonjour" />,
    );
    expect(screen.getByText("Bonjour")).toBeInTheDocument();
    expect(screen.getByText("Vous")).toBeInTheDocument();
  });

  it("renders assistant message", () => {
    renderWithProviders(
      <MessageBubble role="assistant" content="Voici l'analyse." />,
    );
    expect(screen.getByText("XAIS")).toBeInTheDocument();
  });

  it("shows feedback buttons on assistant messages", () => {
    renderWithProviders(
      <MessageBubble
        role="assistant"
        content="Réponse"
        messageId="msg-1"
        onFeedback={mockOnFeedback}
      />,
    );
    expect(screen.getByLabelText("feedbackPositive")).toBeInTheDocument();
    expect(screen.getByLabelText("feedbackNegative")).toBeInTheDocument();
  });

  it("does not show feedback buttons on user messages", () => {
    renderWithProviders(
      <MessageBubble
        role="user"
        content="Ma question"
        messageId="msg-1"
        onFeedback={mockOnFeedback}
      />,
    );
    expect(screen.queryByLabelText("feedbackPositive")).not.toBeInTheDocument();
  });

  it("does not show feedback buttons when streaming", () => {
    renderWithProviders(
      <MessageBubble
        role="assistant"
        content="En cours..."
        messageId="msg-1"
        onFeedback={mockOnFeedback}
        isStreaming
      />,
    );
    expect(screen.queryByLabelText("feedbackPositive")).not.toBeInTheDocument();
  });

  it("calls onFeedback with 'positive' on thumbs up click", () => {
    renderWithProviders(
      <MessageBubble
        role="assistant"
        content="OK"
        messageId="msg-1"
        onFeedback={mockOnFeedback}
      />,
    );
    fireEvent.click(screen.getByLabelText("feedbackPositive"));
    expect(mockOnFeedback).toHaveBeenCalledWith("msg-1", "positive");
  });

  it("calls onFeedback with 'negative' on thumbs down click", () => {
    renderWithProviders(
      <MessageBubble
        role="assistant"
        content="OK"
        messageId="msg-1"
        onFeedback={mockOnFeedback}
      />,
    );
    fireEvent.click(screen.getByLabelText("feedbackNegative"));
    expect(mockOnFeedback).toHaveBeenCalledWith("msg-1", "negative");
  });

  it("toggles feedback off when clicking same button twice", () => {
    renderWithProviders(
      <MessageBubble
        role="assistant"
        content="OK"
        messageId="msg-1"
        onFeedback={mockOnFeedback}
      />,
    );
    const thumbsUp = screen.getByLabelText("feedbackPositive");
    fireEvent.click(thumbsUp);
    fireEvent.click(thumbsUp);
    // Deuxième clic → toggle off → null
    expect(mockOnFeedback).toHaveBeenLastCalledWith("msg-1", null);
  });

  it("shows save as note button for assistant messages", () => {
    renderWithProviders(
      <MessageBubble
        role="assistant"
        content="Note-worthy"
        messageId="msg-1"
        onSaveAsNote={mockOnSaveAsNote}
      />,
    );
    expect(screen.getByLabelText("saveAsNote")).toBeInTheDocument();
  });

  it("calls onSaveAsNote on bookmark click", () => {
    renderWithProviders(
      <MessageBubble
        role="assistant"
        content="À sauver"
        messageId="msg-1"
        onSaveAsNote={mockOnSaveAsNote}
      />,
    );
    fireEvent.click(screen.getByLabelText("saveAsNote"));
    expect(mockOnSaveAsNote).toHaveBeenCalledWith("msg-1", "À sauver");
  });

  it("shows streaming dots when streaming with no content", () => {
    renderWithProviders(
      <MessageBubble role="assistant" content="" isStreaming />,
    );
    // Les dots de streaming sont des spans animés
    const dots = document.querySelectorAll(".animate-bounce");
    expect(dots.length).toBe(3);
  });
});
