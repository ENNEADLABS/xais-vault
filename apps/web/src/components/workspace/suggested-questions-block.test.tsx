import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { mockQueryLoading, mockQuerySuccess } from "@/tests/mocks/query-result";
import { SuggestedQuestionsBlock } from "./suggested-questions-block";
import type { SuggestedQuestion } from "@/hooks/use-suggested-questions";

vi.mock("@/hooks/use-suggested-questions", () => ({
  useSuggestedQuestions: vi.fn(),
}));

const setPrefillMock = vi.fn();
vi.mock("@/stores/workspace-interaction-store", () => ({
  useWorkspaceInteractionStore: (selector: (s: unknown) => unknown) =>
    selector({ setPrefillChatMessage: setPrefillMock }),
}));

import { useSuggestedQuestions } from "@/hooks/use-suggested-questions";

const mockedUse = vi.mocked(useSuggestedQuestions);

function makeQuestion(
  overrides: Partial<SuggestedQuestion> = {},
): SuggestedQuestion {
  return {
    question: "Quel est le chiffre d'affaires ?",
    source_id: "src-1",
    source_name: "Business Plan.pdf",
    ...overrides,
  };
}

describe("SuggestedQuestionsBlock", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("devrait ne rien rendre si la liste de questions est vide", () => {
    mockedUse.mockReturnValue(mockQuerySuccess<SuggestedQuestion[]>([]));

    const { container } = renderWithProviders(
      <SuggestedQuestionsBlock workspaceId="workspace-1" />,
    );

    expect(container.firstChild).toBeNull();
  });

  it("devrait rendre un bouton par question avec son nom de source", () => {
    mockedUse.mockReturnValue(
      mockQuerySuccess<SuggestedQuestion[]>([
        makeQuestion({
          question: "Q1 ?",
          source_id: "s1",
          source_name: "A.pdf",
        }),
        makeQuestion({
          question: "Q2 ?",
          source_id: "s2",
          source_name: "B.pdf",
        }),
        makeQuestion({
          question: "Q3 ?",
          source_id: "s3",
          source_name: "C.pdf",
        }),
      ]),
    );

    renderWithProviders(<SuggestedQuestionsBlock workspaceId="workspace-1" />);

    expect(screen.getByText("Q1 ?")).toBeInTheDocument();
    expect(screen.getByText("Q2 ?")).toBeInTheDocument();
    expect(screen.getByText("Q3 ?")).toBeInTheDocument();
    expect(screen.getByText("A.pdf")).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(3);
  });

  it("devrait appeler setPrefillChatMessage avec le texte au clic", () => {
    mockedUse.mockReturnValue(
      mockQuerySuccess<SuggestedQuestion[]>([
        makeQuestion({ question: "Quelle est la valorisation ?" }),
      ]),
    );

    renderWithProviders(<SuggestedQuestionsBlock workspaceId="workspace-1" />);
    fireEvent.click(screen.getByText("Quelle est la valorisation ?"));

    expect(setPrefillMock).toHaveBeenCalledWith("Quelle est la valorisation ?");
  });

  it("devrait afficher un skeleton pendant le chargement", () => {
    mockedUse.mockReturnValue(mockQueryLoading<SuggestedQuestion[]>());

    const { container } = renderWithProviders(
      <SuggestedQuestionsBlock workspaceId="workspace-1" />,
    );

    // Skeleton rendu → conteneur non nul et pas de bouton
    expect(container.firstChild).not.toBeNull();
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });
});
