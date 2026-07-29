import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { FocusSourceIndicator } from "./focus-source-indicator";
import { useWorkspaceInteractionStore } from "@/stores/workspace-interaction-store";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    if (key === "focusSource" && values?.name) return `Focus : ${values.name}`;
    return key;
  },
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

describe("FocusSourceIndicator", () => {
  beforeEach(() => {
    useWorkspaceInteractionStore.setState({
      ragFilterSourceIds: [],
      focusSourceName: null,
    });
  });

  it("renders nothing when no focus source", () => {
    const { container } = renderWithProviders(<FocusSourceIndicator />);
    expect(container.firstChild).toBeNull();
  });

  it("renders focus source name", () => {
    useWorkspaceInteractionStore.setState({
      ragFilterSourceIds: ["src-1"],
      focusSourceName: "Business_Plan_2026.pdf",
    });
    renderWithProviders(<FocusSourceIndicator />);
    expect(
      screen.getByText("Focus : Business_Plan_2026.pdf"),
    ).toBeInTheDocument();
  });

  it("clears focus source on dismiss click", () => {
    useWorkspaceInteractionStore.setState({
      ragFilterSourceIds: ["src-1"],
      focusSourceName: "BP.pdf",
    });
    renderWithProviders(<FocusSourceIndicator />);

    const dismissBtn = screen.getByLabelText("focusClear");
    fireEvent.click(dismissBtn);

    const state = useWorkspaceInteractionStore.getState();
    expect(state.ragFilterSourceIds).toEqual([]);
    expect(state.focusSourceName).toBeNull();
  });
});
