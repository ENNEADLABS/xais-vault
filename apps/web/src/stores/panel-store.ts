import { create } from "zustand";

interface PanelState {
  leftCollapsed: boolean;
  rightCollapsed: boolean;
  toggleLeft: () => void;
  toggleRight: () => void;
}

export const usePanelStore = create<PanelState>()((set) => ({
  leftCollapsed: false,
  rightCollapsed: false,
  toggleLeft: () => set((s) => ({ leftCollapsed: !s.leftCollapsed })),
  toggleRight: () => set((s) => ({ rightCollapsed: !s.rightCollapsed })),
}));
