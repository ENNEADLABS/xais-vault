import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { ChatInput } from "./chat-input";
import { useWorkspaceInteractionStore } from "@/stores/workspace-interaction-store";
import type { Source } from "@/types/api";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

vi.mock("@/hooks/use-media-query", () => ({
  useMediaQuery: () => true,
  BREAKPOINTS: { md: "(min-width: 768px)" },
}));

function makeSource(overrides: Partial<Source> = {}): Source {
  return {
    id: "src-1",
    workspace_id: "workspace-1",
    organization_id: "org-1",
    name: "Business_Plan.pdf",
    type: "pdf",
    file_size_bytes: 1024,
    status: "ready",
    error_message: null,
    page_count: 42,
    word_count: 5000,
    summary: null,
    topics: null,
    suggested_questions: null,
    created_at: "2026-01-01",
    updated_at: "2026-01-01",
    ...overrides,
  };
}

describe("ChatInput", () => {
  const mockOnSend = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    useWorkspaceInteractionStore.setState({
      prefillChatMessage: null,
      scrollToSourceId: null,
      ragFilterSourceIds: [],
      focusSourceName: null,
    });
  });

  it("renders textarea", () => {
    renderWithProviders(<ChatInput onSend={mockOnSend} isStreaming={false} />);
    expect(
      screen.getByPlaceholderText("inputPlaceholder"),
    ).toBeInTheDocument();
  });

  it("sends message on button click", () => {
    renderWithProviders(<ChatInput onSend={mockOnSend} isStreaming={false} />);
    const textarea = screen.getByPlaceholderText("inputPlaceholder");
    fireEvent.change(textarea, { target: { value: "Hello world" } });
    const sendBtn = screen.getByRole("button");
    fireEvent.click(sendBtn);
    expect(mockOnSend).toHaveBeenCalledWith("Hello world");
  });

  it("clears textarea after send", () => {
    renderWithProviders(<ChatInput onSend={mockOnSend} isStreaming={false} />);
    const textarea = screen.getByPlaceholderText(
      "inputPlaceholder",
    ) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "test" } });
    fireEvent.click(screen.getByRole("button"));
    expect(textarea.value).toBe("");
  });

  it("disables textarea when streaming", () => {
    renderWithProviders(<ChatInput onSend={mockOnSend} isStreaming />);
    const textarea = screen.getByPlaceholderText("inputPlaceholder");
    expect(textarea).toBeDisabled();
  });

  it("does not send empty message", () => {
    renderWithProviders(<ChatInput onSend={mockOnSend} isStreaming={false} />);
    fireEvent.click(screen.getByRole("button"));
    expect(mockOnSend).not.toHaveBeenCalled();
  });

  describe("prefill from store", () => {
    it("fills textarea when prefillChatMessage is set", async () => {
      renderWithProviders(
        <ChatInput onSend={mockOnSend} isStreaming={false} />,
      );
      const textarea = screen.getByPlaceholderText(
        "inputPlaceholder",
      ) as HTMLTextAreaElement;

      // Simule un clic topic dans SourceCard
      useWorkspaceInteractionStore.getState().setPrefillChatMessage("Parle-moi de Revenus");

      await waitFor(() => {
        expect(textarea.value).toBe("Parle-moi de Revenus");
      });
    });

    it("clears store after consuming prefill", async () => {
      renderWithProviders(
        <ChatInput onSend={mockOnSend} isStreaming={false} />,
      );

      useWorkspaceInteractionStore.getState().setPrefillChatMessage("Test prefill");

      await waitFor(() => {
        expect(useWorkspaceInteractionStore.getState().prefillChatMessage).toBeNull();
      });
    });
  });

  describe("@ mention", () => {
    const sources = [
      makeSource({ id: "src-1", name: "Business_Plan.pdf" }),
      makeSource({ id: "src-2", name: "Financial_Model.xlsx", type: "xlsx" }),
      makeSource({ id: "src-3", name: "Rapport_Audit.pdf", status: "processing" }),
    ];

    it("shows mention dropdown when typing @", () => {
      renderWithProviders(
        <ChatInput onSend={mockOnSend} isStreaming={false} sources={sources} />,
      );
      const textarea = screen.getByPlaceholderText("inputPlaceholder");
      fireEvent.change(textarea, { target: { value: "@" } });

      // Seules les sources "ready" apparaissent dans le dropdown
      expect(screen.getByText("Business_Plan.pdf")).toBeInTheDocument();
      expect(screen.getByText("Financial_Model.xlsx")).toBeInTheDocument();
      // "processing" sources are excluded
      expect(screen.queryByText("Rapport_Audit.pdf")).not.toBeInTheDocument();
    });

    it("filters mention dropdown as user types", () => {
      renderWithProviders(
        <ChatInput onSend={mockOnSend} isStreaming={false} sources={sources} />,
      );
      const textarea = screen.getByPlaceholderText("inputPlaceholder");
      fireEvent.change(textarea, { target: { value: "@Busi" } });

      expect(screen.getByText("Business_Plan.pdf")).toBeInTheDocument();
      expect(screen.queryByText("Financial_Model.xlsx")).not.toBeInTheDocument();
    });

    it("hides dropdown when space is typed after @", () => {
      renderWithProviders(
        <ChatInput onSend={mockOnSend} isStreaming={false} sources={sources} />,
      );
      const textarea = screen.getByPlaceholderText("inputPlaceholder");
      fireEvent.change(textarea, { target: { value: "@Business " } });

      expect(screen.queryByText("Business_Plan.pdf")).not.toBeInTheDocument();
    });

    it("selects mention and activates focus source", () => {
      renderWithProviders(
        <ChatInput onSend={mockOnSend} isStreaming={false} sources={sources} />,
      );
      const textarea = screen.getByPlaceholderText("inputPlaceholder") as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: "@" } });

      // Simuler mouseDown au lieu de click (car mouseDown avec preventDefault)
      const option = screen.getByText("Business_Plan.pdf");
      fireEvent.mouseDown(option);

      // Le textarea doit contenir le nom de la source
      expect(textarea.value).toContain("@Business_Plan.pdf");

      // Le store doit avoir le focus source activé
      const state = useWorkspaceInteractionStore.getState();
      expect(state.ragFilterSourceIds).toEqual(["src-1"]);
      expect(state.focusSourceName).toBe("Business_Plan.pdf");
    });
  });

  describe("context label", () => {
    it("shows context label when provided", () => {
      renderWithProviders(
        <ChatInput
          onSend={mockOnSend}
          isStreaming={false}
          contextLabel="Basé sur 5 sources · 120 pages"
        />,
      );
      expect(
        screen.getByText("Basé sur 5 sources · 120 pages"),
      ).toBeInTheDocument();
    });
  });
});
