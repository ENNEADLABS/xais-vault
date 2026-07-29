import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { mockQueryLoading, mockQuerySuccess } from "@/tests/mocks/query-result";
import type { PaginatedResponse } from "@/lib/api";
import { WebhookDeliveriesDialog } from "./webhook-deliveries-dialog";
import type { WebhookDelivery } from "@/types/api";

type DeliveriesResult = PaginatedResponse<WebhookDelivery>;

vi.mock("@/lib/hooks/use-webhooks", () => ({
  useWebhookDeliveries: vi.fn(),
}));

import { useWebhookDeliveries } from "@/lib/hooks/use-webhooks";

const WEBHOOK_ID = "wh-123";

const DELIVERY_DELIVERED: WebhookDelivery = {
  id: "d1",
  webhook_id: WEBHOOK_ID,
  event_type: "scan.completed",
  payload: {},
  status: "delivered",
  attempt: 1,
  http_status: 200,
  response_body: "OK",
  next_retry_at: null,
  created_at: "2025-01-01T10:00:00Z",
  delivered_at: "2025-01-01T10:00:01Z",
};

const DELIVERY_FAILED: WebhookDelivery = {
  ...DELIVERY_DELIVERED,
  id: "d2",
  event_type: "source.ready",
  status: "failed",
  http_status: 500,
  delivered_at: null,
};

describe("WebhookDeliveriesDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le skeleton en cours de chargement", () => {
    vi.mocked(useWebhookDeliveries).mockReturnValue(mockQueryLoading<DeliveriesResult>());

    renderWithProviders(
      <WebhookDeliveriesDialog
        webhookId={WEBHOOK_ID}
        open={true}
        onOpenChange={vi.fn()}
      />,
    );
    expect(
      document.body.querySelector('[data-slot="skeleton"]'),
    ).toBeInTheDocument();
  });

  it("affiche l'état vide quand aucune livraison", () => {
    vi.mocked(useWebhookDeliveries).mockReturnValue(
      mockQuerySuccess<DeliveriesResult>({ data: [], total: 0, page: 1, per_page: 20, pages: 0 }),
    );

    renderWithProviders(
      <WebhookDeliveriesDialog
        webhookId={WEBHOOK_ID}
        open={true}
        onOpenChange={vi.fn()}
      />,
    );
    expect(screen.getByText("webhooks.deliveriesEmpty")).toBeInTheDocument();
  });

  it("affiche les livraisons dans un tableau", () => {
    vi.mocked(useWebhookDeliveries).mockReturnValue(
      mockQuerySuccess<DeliveriesResult>({
        data: [DELIVERY_DELIVERED, DELIVERY_FAILED],
        total: 2,
        page: 1,
        per_page: 20,
        pages: 1,
      }),
    );

    renderWithProviders(
      <WebhookDeliveriesDialog
        webhookId={WEBHOOK_ID}
        open={true}
        onOpenChange={vi.fn()}
      />,
    );
    expect(screen.getByText("scan.completed")).toBeInTheDocument();
    expect(screen.getByText("source.ready")).toBeInTheDocument();
    expect(screen.getByText("200")).toBeInTheDocument();
    expect(screen.getByText("500")).toBeInTheDocument();
  });

  it("affiche le bon badge pour livraison réussie", () => {
    vi.mocked(useWebhookDeliveries).mockReturnValue(
      mockQuerySuccess<DeliveriesResult>({ data: [DELIVERY_DELIVERED], total: 1, page: 1, per_page: 20, pages: 1 }),
    );

    renderWithProviders(
      <WebhookDeliveriesDialog
        webhookId={WEBHOOK_ID}
        open={true}
        onOpenChange={vi.fn()}
      />,
    );
    expect(screen.getByText("webhooks.statusDelivered")).toBeInTheDocument();
  });

  it("affiche le bon badge pour livraison échouée", () => {
    vi.mocked(useWebhookDeliveries).mockReturnValue(
      mockQuerySuccess<DeliveriesResult>({ data: [DELIVERY_FAILED], total: 1, page: 1, per_page: 20, pages: 1 }),
    );

    renderWithProviders(
      <WebhookDeliveriesDialog
        webhookId={WEBHOOK_ID}
        open={true}
        onOpenChange={vi.fn()}
      />,
    );
    expect(screen.getByText("webhooks.statusFailed")).toBeInTheDocument();
  });

  it("affiche '—' pour http_status null", () => {
    vi.mocked(useWebhookDeliveries).mockReturnValue(
      mockQuerySuccess<DeliveriesResult>({
        data: [{ ...DELIVERY_FAILED, http_status: null }],
        total: 1,
        page: 1,
        per_page: 20,
        pages: 1,
      }),
    );

    renderWithProviders(
      <WebhookDeliveriesDialog
        webhookId={WEBHOOK_ID}
        open={true}
        onOpenChange={vi.fn()}
      />,
    );
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
