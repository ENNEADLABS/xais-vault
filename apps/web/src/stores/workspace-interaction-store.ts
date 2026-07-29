import { create } from "zustand";

interface WorkspaceInteractionState {
  /** Message à pré-remplir dans le chat */
  prefillChatMessage: string | null;
  setPrefillChatMessage: (msg: string | null) => void;

  /** Source à scroller + highlight */
  scrollToSourceId: string | null;
  setScrollToSourceId: (id: string | null) => void;

  /** Source à highlight temporairement (clic citation) */
  highlightSourceId: string | null;
  highlightPage: number | null;
  setHighlightSource: (sourceId: string, page?: number) => void;
  clearHighlight: () => void;

  /** Source IDs pour filtrage RAG (focus mode) */
  ragFilterSourceIds: string[];
  focusSourceName: string | null;
  setFocusSource: (id: string, name: string) => void;
  clearFocusSource: () => void;
}

export const useWorkspaceInteractionStore = create<WorkspaceInteractionState>()(
  (set) => ({
    prefillChatMessage: null,
    setPrefillChatMessage: (msg) => set({ prefillChatMessage: msg }),

    scrollToSourceId: null,
    setScrollToSourceId: (id) => set({ scrollToSourceId: id }),

    highlightSourceId: null,
    highlightPage: null,
    setHighlightSource: (sourceId, page) =>
      set({ highlightSourceId: sourceId, highlightPage: page ?? null }),
    clearHighlight: () => set({ highlightSourceId: null, highlightPage: null }),

    ragFilterSourceIds: [],
    focusSourceName: null,
    setFocusSource: (id, name) =>
      set({ ragFilterSourceIds: [id], focusSourceName: name }),
    clearFocusSource: () => set({ ragFilterSourceIds: [], focusSourceName: null }),
  }),
);
