import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { mockQuerySuccess, mockQueryLoading } from "@/tests/mocks/query-result";
import { SourcesPanel } from "./sources-panel";
import type { Source } from "@/types/api";
import type { ApiResponse } from "@/lib/api";

const mockUseSources = vi.fn();

vi.mock("@/lib/hooks/use-sources", () => ({
  useSources: (...args: unknown[]) => mockUseSources(...args),
}));

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

// Mock SourceUploadDialog pour éviter les dépendances lourdes
vi.mock("./source-upload-dialog", () => ({
  SourceUploadDialog: () => null,
}));

const makeSource = (overrides: Partial<Source> = {}): Source => ({
  id: "src-1",
  workspace_id: "workspace-1",
  organization_id: "org-1",
  name: "Business_Plan.pdf",
  type: "pdf",
  file_size_bytes: 2400000,
  status: "ready",
  error_message: null,
  page_count: 42,
  word_count: 12340,
  summary: "Un plan d'affaires détaillé",
  topics: ["Revenus", "Marché"],
  suggested_questions: ["Quel est le CA ?"],
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
  ...overrides,
});

const SOURCES: Source[] = [
  makeSource({ id: "src-1", name: "Business_Plan.pdf", type: "pdf", page_count: 42, word_count: 10000 }),
  makeSource({ id: "src-2", name: "Financials.xlsx", type: "xlsx", page_count: 5, word_count: 2000, summary: "Données financières" }),
  makeSource({ id: "src-3", name: "Pitch.docx", type: "docx", page_count: 10, word_count: 3000, summary: "Pitch deck résumé" }),
];

function mockWithSources(sources: Source[]) {
  mockUseSources.mockReturnValue(
    mockQuerySuccess<ApiResponse<Source[]>>({ data: sources }),
  );
}

function mockLoading() {
  mockUseSources.mockReturnValue(mockQueryLoading<ApiResponse<Source[]>>());
}

describe("SourcesPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("loading state", () => {
    it("shows skeletons while loading", () => {
      mockLoading();
      const { container } = renderWithProviders(
        <SourcesPanel workspaceId="workspace-1" />,
      );
      // SourceCardSkeleton renders divs with aria-hidden="true"
      const skeletons = container.querySelectorAll("[aria-hidden='true']");
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe("empty state", () => {
    it("shows empty state when no sources", () => {
      mockWithSources([]);
      renderWithProviders(<SourcesPanel workspaceId="workspace-1" />);
      expect(screen.getByText("noSources")).toBeInTheDocument();
    });

    it("shows upload button when empty", () => {
      mockWithSources([]);
      renderWithProviders(<SourcesPanel workspaceId="workspace-1" />);
      expect(screen.getByText("uploadSource")).toBeInTheDocument();
    });
  });

  describe("with sources", () => {
    it("renders all source cards", () => {
      mockWithSources(SOURCES);
      renderWithProviders(<SourcesPanel workspaceId="workspace-1" />);
      expect(screen.getByText("Business_Plan.pdf")).toBeInTheDocument();
      expect(screen.getByText("Financials.xlsx")).toBeInTheDocument();
      expect(screen.getByText("Pitch.docx")).toBeInTheDocument();
    });

    it("shows source count in header", () => {
      mockWithSources(SOURCES);
      renderWithProviders(<SourcesPanel workspaceId="workspace-1" />);
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("shows type breakdown in stats", () => {
      mockWithSources(SOURCES);
      renderWithProviders(<SourcesPanel workspaceId="workspace-1" />);
      // "1 PDF · 1 XLSX · 1 DOCX"
      expect(screen.getByText(/PDF/)).toBeInTheDocument();
      expect(screen.getByText(/XLSX/)).toBeInTheDocument();
      expect(screen.getByText(/DOCX/)).toBeInTheDocument();
    });

    it("shows aggregated page/word stats", () => {
      mockWithSources(SOURCES);
      renderWithProviders(<SourcesPanel workspaceId="workspace-1" />);
      // totalPages = 42+5+10 = 57, totalWords = 10000+2000+3000 = 15000
      expect(screen.getByText(/sourcePages:count=57/)).toBeInTheDocument();
      expect(screen.getByText(/sourceWords:count=15,000/)).toBeInTheDocument();
    });
  });

  describe("search", () => {
    it("renders search input when sources exist", () => {
      mockWithSources(SOURCES);
      renderWithProviders(<SourcesPanel workspaceId="workspace-1" />);
      expect(
        screen.getByPlaceholderText("searchSources"),
      ).toBeInTheDocument();
    });

    it("filters sources by name", () => {
      mockWithSources(SOURCES);
      renderWithProviders(<SourcesPanel workspaceId="workspace-1" />);
      const input = screen.getByPlaceholderText("searchSources");
      fireEvent.change(input, { target: { value: "Pitch" } });
      expect(screen.getByText("Pitch.docx")).toBeInTheDocument();
      expect(screen.queryByText("Business_Plan.pdf")).not.toBeInTheDocument();
      expect(screen.queryByText("Financials.xlsx")).not.toBeInTheDocument();
    });

    it("filters sources by summary", () => {
      mockWithSources(SOURCES);
      renderWithProviders(<SourcesPanel workspaceId="workspace-1" />);
      const input = screen.getByPlaceholderText("searchSources");
      fireEvent.change(input, { target: { value: "financières" } });
      expect(screen.getByText("Financials.xlsx")).toBeInTheDocument();
      expect(screen.queryByText("Business_Plan.pdf")).not.toBeInTheDocument();
    });

    it("shows no results message when search has no matches", () => {
      mockWithSources(SOURCES);
      renderWithProviders(<SourcesPanel workspaceId="workspace-1" />);
      const input = screen.getByPlaceholderText("searchSources");
      fireEvent.change(input, { target: { value: "zzzznonexistent" } });
      expect(screen.getByText("noSearchResults")).toBeInTheDocument();
    });

    it("does not show search when no sources", () => {
      mockWithSources([]);
      renderWithProviders(<SourcesPanel workspaceId="workspace-1" />);
      expect(
        screen.queryByPlaceholderText("searchSources"),
      ).not.toBeInTheDocument();
    });
  });

  describe("collapsed view", () => {
    it("renders vertical sources label", () => {
      mockWithSources(SOURCES);
      renderWithProviders(
        <SourcesPanel workspaceId="workspace-1" collapsed onCollapse={vi.fn()} />,
      );
      expect(screen.getByText("sources")).toBeInTheDocument();
    });

    it("renders expand button", () => {
      mockWithSources(SOURCES);
      const onCollapse = vi.fn();
      renderWithProviders(
        <SourcesPanel workspaceId="workspace-1" collapsed onCollapse={onCollapse} />,
      );
      const expandBtn = screen.getAllByRole("button")[0]!;
      fireEvent.click(expandBtn);
      expect(onCollapse).toHaveBeenCalled();
    });
  });

  describe("drag and drop", () => {
    it("shows drag overlay on dragenter", () => {
      mockWithSources(SOURCES);
      const { container } = renderWithProviders(
        <SourcesPanel workspaceId="workspace-1" />,
      );
      const dropZone = container.firstChild as HTMLElement;
      fireEvent.dragEnter(dropZone, {
        dataTransfer: { files: [], types: ["Files"] },
      });
      expect(screen.getByText("dropFilesHere")).toBeInTheDocument();
    });
  });
});
