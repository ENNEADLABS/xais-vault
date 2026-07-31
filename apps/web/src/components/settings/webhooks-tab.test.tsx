import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { mockQueryLoading, mockQuerySuccess } from "@/tests/mocks/query-result";
import type { PaginatedResponse } from "@/lib/api";
import { WebhooksTab } from "./webhooks-tab";
import type { Webhook } from "@/types/api";

type WebhooksResult = PaginatedResponse<Webhook>;

vi.mock("@/lib/hooks/use-webhooks", () => ({
  useWebhooks: vi.fn(),
  useCreateWebhook: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateWebhook: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteWebhook: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useTestWebhook: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useRotateWebhookSecret: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
  useWebhookDeliveries: vi.fn(() => ({ data: undefined, isLoading: true })),
}));

import { useWebhooks } from "@/lib/hooks/use-webhooks";

const WEBHOOK: Webhook = {
  id: "wh-1",
  url: "https://example.com/hook",
  events: ["scan.completed", "insight.created"],
  is_active: true,
  created_by: "user-1",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
};

describe("WebhooksTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le skeleton en cours de chargement", () => {
    vi.mocked(useWebhooks).mockReturnValue(mockQueryLoading<WebhooksResult>());

    const { container } = renderWithProviders(<WebhooksTab />);
    const skeletons = container.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("affiche l'état vide quand aucun webhook", () => {
    vi.mocked(useWebhooks).mockReturnValue(
      mockQuerySuccess<WebhooksResult>({ data: [], total: 0, page: 1, per_page: 20, pages: 0 }),
    );

    renderWithProviders(<WebhooksTab />);
    expect(screen.getByText("webhooks.noWebhooks")).toBeInTheDocument();
    expect(screen.getByText("webhooks.noWebhooksHint")).toBeInTheDocument();
  });

  it("affiche la liste des webhooks", () => {
    vi.mocked(useWebhooks).mockReturnValue(
      mockQuerySuccess<WebhooksResult>({ data: [WEBHOOK], total: 1, page: 1, per_page: 20, pages: 1 }),
    );

    renderWithProviders(<WebhooksTab />);
    expect(screen.getByText("https://example.com/hook")).toBeInTheDocument();
  });

  it("affiche le bouton Créer", () => {
    vi.mocked(useWebhooks).mockReturnValue(
      mockQuerySuccess<WebhooksResult>({ data: [], total: 0, page: 1, per_page: 20, pages: 0 }),
    );

    renderWithProviders(<WebhooksTab />);
    expect(screen.getByText("webhooks.create")).toBeInTheDocument();
  });

  it("ouvre le dialog de création au clic sur Créer", () => {
    vi.mocked(useWebhooks).mockReturnValue(
      mockQuerySuccess<WebhooksResult>({ data: [], total: 0, page: 1, per_page: 20, pages: 0 }),
    );

    renderWithProviders(<WebhooksTab />);
    const createBtn = screen.getByText("webhooks.create");
    fireEvent.click(createBtn);
    expect(screen.getByLabelText("webhooks.urlLabel")).toBeInTheDocument();
  });

  it("affiche les badges d'events pour chaque webhook", () => {
    vi.mocked(useWebhooks).mockReturnValue(
      mockQuerySuccess<WebhooksResult>({ data: [WEBHOOK], total: 1, page: 1, per_page: 20, pages: 1 }),
    );

    renderWithProviders(<WebhooksTab />);
    expect(screen.getByText("Scan completed")).toBeInTheDocument();
    expect(screen.getByText("Insight created")).toBeInTheDocument();
  });
});
