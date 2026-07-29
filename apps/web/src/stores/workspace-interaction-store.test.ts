import { describe, it, expect, beforeEach } from "vitest";
import { useWorkspaceInteractionStore } from "./workspace-interaction-store";

describe("useWorkspaceInteractionStore", () => {
  beforeEach(() => {
    // Reset store entre chaque test
    useWorkspaceInteractionStore.setState({
      prefillChatMessage: null,
      scrollToSourceId: null,
      highlightSourceId: null,
      highlightPage: null,
      ragFilterSourceIds: [],
      focusSourceName: null,
    });
  });

  describe("prefillChatMessage", () => {
    it("starts as null", () => {
      expect(useWorkspaceInteractionStore.getState().prefillChatMessage).toBeNull();
    });

    it("sets a prefill message", () => {
      useWorkspaceInteractionStore.getState().setPrefillChatMessage("Parle-moi de Revenus");
      expect(useWorkspaceInteractionStore.getState().prefillChatMessage).toBe(
        "Parle-moi de Revenus",
      );
    });

    it("clears the prefill message with null", () => {
      useWorkspaceInteractionStore.getState().setPrefillChatMessage("test");
      useWorkspaceInteractionStore.getState().setPrefillChatMessage(null);
      expect(useWorkspaceInteractionStore.getState().prefillChatMessage).toBeNull();
    });
  });

  describe("scrollToSourceId", () => {
    it("starts as null", () => {
      expect(useWorkspaceInteractionStore.getState().scrollToSourceId).toBeNull();
    });

    it("sets a focus source id", () => {
      useWorkspaceInteractionStore.getState().setScrollToSourceId("src-123");
      expect(useWorkspaceInteractionStore.getState().scrollToSourceId).toBe("src-123");
    });

    it("clears focus with null", () => {
      useWorkspaceInteractionStore.getState().setScrollToSourceId("src-123");
      useWorkspaceInteractionStore.getState().setScrollToSourceId(null);
      expect(useWorkspaceInteractionStore.getState().scrollToSourceId).toBeNull();
    });
  });

  describe("highlightSource", () => {
    it("starts as null", () => {
      const state = useWorkspaceInteractionStore.getState();
      expect(state.highlightSourceId).toBeNull();
      expect(state.highlightPage).toBeNull();
    });

    it("sets highlight source with page", () => {
      useWorkspaceInteractionStore.getState().setHighlightSource("src-1", 42);
      const state = useWorkspaceInteractionStore.getState();
      expect(state.highlightSourceId).toBe("src-1");
      expect(state.highlightPage).toBe(42);
    });

    it("sets highlight source without page (defaults to null)", () => {
      useWorkspaceInteractionStore.getState().setHighlightSource("src-1");
      const state = useWorkspaceInteractionStore.getState();
      expect(state.highlightSourceId).toBe("src-1");
      expect(state.highlightPage).toBeNull();
    });

    it("clears highlight", () => {
      useWorkspaceInteractionStore.getState().setHighlightSource("src-1", 5);
      useWorkspaceInteractionStore.getState().clearHighlight();
      const state = useWorkspaceInteractionStore.getState();
      expect(state.highlightSourceId).toBeNull();
      expect(state.highlightPage).toBeNull();
    });
  });

  describe("focusSource (RAG filter)", () => {
    it("starts empty", () => {
      const state = useWorkspaceInteractionStore.getState();
      expect(state.ragFilterSourceIds).toEqual([]);
      expect(state.focusSourceName).toBeNull();
    });

    it("sets focus source with id and name", () => {
      useWorkspaceInteractionStore.getState().setFocusSource("src-99", "Business_Plan.pdf");
      const state = useWorkspaceInteractionStore.getState();
      expect(state.ragFilterSourceIds).toEqual(["src-99"]);
      expect(state.focusSourceName).toBe("Business_Plan.pdf");
    });

    it("clears focus source", () => {
      useWorkspaceInteractionStore.getState().setFocusSource("src-99", "BP.pdf");
      useWorkspaceInteractionStore.getState().clearFocusSource();
      const state = useWorkspaceInteractionStore.getState();
      expect(state.ragFilterSourceIds).toEqual([]);
      expect(state.focusSourceName).toBeNull();
    });
  });
});
