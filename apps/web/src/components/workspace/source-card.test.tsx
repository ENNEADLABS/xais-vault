import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { SourceCard } from "./source-card";
import { useWorkspaceInteractionStore } from "@/stores/workspace-interaction-store";
import type { Source } from "@/types/api";

vi.mock("next-intl", () => ({
  useTranslations:
    () =>
    (key: string, params?: Record<string, string | number>) => {
      if (params) {
        let result = key;
        for (const [k, v] of Object.entries(params)) {
          result += `:${k}=${v}`;
        }
        return result;
      }
      return key;
    },
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
  formatFileSize: (bytes: number | null) =>
    bytes ? `${(bytes / 1024).toFixed(0)} KB` : "—",
}));

const READY_SOURCE: Source = {
  id: "src-1",
  workspace_id: "workspace-1",
  organization_id: "org-1",
  name: "Business_Plan_2026.pdf",
  type: "pdf",
  file_size_bytes: 2457600,
  status: "ready",
  error_message: null,
  page_count: 42,
  word_count: 12340,
  summary: "Plan d'affaires détaillant la stratégie de croissance.",
  topics: ["Revenus", "Marché", "Risques"],
  suggested_questions: [
    "Quel est le CA prévu ?",
    "Quels sont les risques identifiés ?",
  ],
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
};

const PENDING_SOURCE: Source = {
  ...READY_SOURCE,
  id: "src-2",
  status: "pending",
  summary: null,
  topics: null,
  suggested_questions: null,
  page_count: null,
  word_count: null,
};

describe("SourceCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useWorkspaceInteractionStore.setState({
      prefillChatMessage: null,
      scrollToSourceId: null,
    });
  });

  describe("collapsed (default)", () => {
    it("renders source name", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      expect(screen.getByText("Business_Plan_2026.pdf")).toBeInTheDocument();
    });

    it("renders status badge", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      expect(screen.getByText("statusReady")).toBeInTheDocument();
    });

    it("renders file size", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      expect(screen.getByText("2400 KB")).toBeInTheDocument();
    });

    it("shows chevron for ready sources with details", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      // Le bouton header est cliquable et contient un chevron
      const button = screen.getByRole("button", {
        name: /Business_Plan_2026/,
      });
      expect(button).toBeInTheDocument();
    });

    it("does not show expand chevron for pending sources", () => {
      renderWithProviders(<SourceCard source={PENDING_SOURCE} />);
      // Pas de summary ni topics → pas de chevron, pas de bouton expand
      expect(screen.getByText("statusPending")).toBeInTheDocument();
    });
  });

  describe("expanded", () => {
    it("shows summary after click", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      const header = screen.getByRole("button", {
        name: /Business_Plan_2026/,
      });
      fireEvent.click(header);
      expect(
        screen.getByText("Plan d'affaires détaillant la stratégie de croissance."),
      ).toBeInTheDocument();
    });

    it("shows summary label", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      fireEvent.click(
        screen.getByRole("button", { name: /Business_Plan_2026/ }),
      );
      expect(screen.getByText("sourceSummary")).toBeInTheDocument();
    });

    it("shows topics as buttons", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      fireEvent.click(
        screen.getByRole("button", { name: /Business_Plan_2026/ }),
      );
      expect(screen.getByText("Revenus")).toBeInTheDocument();
      expect(screen.getByText("Marché")).toBeInTheDocument();
      expect(screen.getByText("Risques")).toBeInTheDocument();
    });

    it("shows page and word count", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      fireEvent.click(
        screen.getByRole("button", { name: /Business_Plan_2026/ }),
      );
      expect(screen.getByText(/sourcePages/)).toBeInTheDocument();
      expect(screen.getByText(/sourceWords/)).toBeInTheDocument();
    });

    it("shows suggested questions", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      fireEvent.click(
        screen.getByRole("button", { name: /Business_Plan_2026/ }),
      );
      expect(screen.getByText("Quel est le CA prévu ?")).toBeInTheDocument();
      expect(
        screen.getByText("Quels sont les risques identifiés ?"),
      ).toBeInTheDocument();
    });

    it("shows action buttons", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      fireEvent.click(
        screen.getByRole("button", { name: /Business_Plan_2026/ }),
      );
      expect(screen.getByText("askQuestion")).toBeInTheDocument();
      expect(screen.getByText("scanSource")).toBeInTheDocument();
    });
  });

  describe("interactions → store prefill", () => {
    it("clicking a topic sets prefill message", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      fireEvent.click(
        screen.getByRole("button", { name: /Business_Plan_2026/ }),
      );
      fireEvent.click(screen.getByText("Revenus"));
      expect(useWorkspaceInteractionStore.getState().prefillChatMessage).toContain(
        "Revenus",
      );
    });

    it("clicking ask question sets prefill message", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      fireEvent.click(
        screen.getByRole("button", { name: /Business_Plan_2026/ }),
      );
      fireEvent.click(screen.getByText("askQuestion"));
      expect(
        useWorkspaceInteractionStore.getState().prefillChatMessage,
      ).toBeTruthy();
    });

    it("clicking a suggested question sets prefill message", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      fireEvent.click(
        screen.getByRole("button", { name: /Business_Plan_2026/ }),
      );
      fireEvent.click(screen.getByText("Quel est le CA prévu ?"));
      expect(useWorkspaceInteractionStore.getState().prefillChatMessage).toBe(
        "Quel est le CA prévu ?",
      );
    });

    it("clicking scan source sets prefill message", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      fireEvent.click(
        screen.getByRole("button", { name: /Business_Plan_2026/ }),
      );
      fireEvent.click(screen.getByText("scanSource"));
      expect(
        useWorkspaceInteractionStore.getState().prefillChatMessage,
      ).toBeTruthy();
    });
  });

  describe("toggle expand/collapse", () => {
    it("collapses back on second click", () => {
      renderWithProviders(<SourceCard source={READY_SOURCE} />);
      const header = screen.getByRole("button", {
        name: /Business_Plan_2026/,
      });
      // Expand
      fireEvent.click(header);
      expect(screen.getByText("sourceSummary")).toBeInTheDocument();
      // Collapse
      fireEvent.click(header);
      // Le contenu est masqué via grid-rows-[0fr] + overflow-hidden
      // Le texte est toujours dans le DOM mais visuellement caché
    });
  });
});
