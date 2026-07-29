import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { CitationBadge } from "./citation-badge";
import { useWorkspaceInteractionStore } from "@/stores/workspace-interaction-store";
import { usePanelStore } from "@/stores/panel-store";
import type { Citation } from "@/types/api";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    if (key === "citationPage" && values?.page) return `p.${values.page}`;
    return key;
  },
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

const baseCitation: Citation = {
  source_id: "src-1",
  source_name: "Business_Plan.pdf",
  page_number: 5,
  section_title: "Revenus",
  quote: "Le chiffre d'affaires est en hausse de 20%.",
};

describe("CitationBadge", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useWorkspaceInteractionStore.setState({
      highlightSourceId: null,
      highlightPage: null,
      scrollToSourceId: null,
    });
    usePanelStore.setState({ leftCollapsed: false });
  });

  it("renders source name with page number", () => {
    renderWithProviders(<CitationBadge citation={baseCitation} />);
    expect(screen.getByText("Business_Plan.pdf p.5")).toBeInTheDocument();
  });

  it("renders source name without page number", () => {
    const citation = { ...baseCitation, page_number: null };
    renderWithProviders(<CitationBadge citation={citation} />);
    expect(screen.getByText("Business_Plan.pdf")).toBeInTheDocument();
  });

  it("shows quote as title attribute", () => {
    renderWithProviders(<CitationBadge citation={baseCitation} />);
    const btn = screen.getByRole("button");
    expect(btn).toHaveAttribute("title", baseCitation.quote);
  });

  it("sets highlight source on click", () => {
    renderWithProviders(<CitationBadge citation={baseCitation} />);
    fireEvent.click(screen.getByRole("button"));

    const state = useWorkspaceInteractionStore.getState();
    expect(state.highlightSourceId).toBe("src-1");
    expect(state.highlightPage).toBe(5);
  });

  it("sets scrollToSourceId on click", () => {
    renderWithProviders(<CitationBadge citation={baseCitation} />);
    fireEvent.click(screen.getByRole("button"));

    expect(useWorkspaceInteractionStore.getState().scrollToSourceId).toBe("src-1");
  });

  it("expands left panel if collapsed", () => {
    usePanelStore.setState({ leftCollapsed: true });
    renderWithProviders(<CitationBadge citation={baseCitation} />);
    fireEvent.click(screen.getByRole("button"));

    expect(usePanelStore.getState().leftCollapsed).toBe(false);
  });

  it("does not toggle left panel if already expanded", () => {
    usePanelStore.setState({ leftCollapsed: false });
    renderWithProviders(<CitationBadge citation={baseCitation} />);
    fireEvent.click(screen.getByRole("button"));

    // toggleLeft n'est appelé que si collapsed → le panneau reste ouvert
    expect(usePanelStore.getState().leftCollapsed).toBe(false);
  });

  it("calls custom onClick callback", () => {
    const onClick = vi.fn();
    renderWithProviders(
      <CitationBadge citation={baseCitation} onClick={onClick} />,
    );
    fireEvent.click(screen.getByRole("button"));

    expect(onClick).toHaveBeenCalledOnce();
  });
});
