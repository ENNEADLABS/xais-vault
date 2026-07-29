import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { WebhookRow } from "./webhook-row";
import type { Webhook } from "@/types/api";

const mockMutateAsync = vi.fn();

vi.mock("@/lib/hooks/use-webhooks", () => ({
  useUpdateWebhook: vi.fn(() => ({ mutateAsync: mockMutateAsync })),
  useDeleteWebhook: vi.fn(() => ({ mutateAsync: mockMutateAsync })),
  useTestWebhook: vi.fn(() => ({ mutateAsync: mockMutateAsync })),
  useRotateWebhookSecret: vi.fn(() => ({ mutateAsync: mockMutateAsync })),
  useWebhookDeliveries: vi.fn(() => ({ data: undefined, isLoading: false })),
}));

const WEBHOOK_ACTIVE: Webhook = {
  id: "wh-1",
  url: "https://example.com/webhook",
  events: ["scan.completed", "insight.created"],
  is_active: true,
  created_by: "user-1",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
};

const WEBHOOK_INACTIVE: Webhook = { ...WEBHOOK_ACTIVE, is_active: false };

describe("WebhookRow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutateAsync.mockResolvedValue({ data: {} });
  });

  it("affiche l'URL du webhook", () => {
    renderWithProviders(<WebhookRow webhook={WEBHOOK_ACTIVE} />);
    expect(screen.getByText("https://example.com/webhook")).toBeInTheDocument();
  });

  it("affiche les badges d'events", () => {
    renderWithProviders(<WebhookRow webhook={WEBHOOK_ACTIVE} />);
    expect(screen.getByText("Scan completed")).toBeInTheDocument();
    expect(screen.getByText("Insight created")).toBeInTheDocument();
  });

  it("affiche le badge Actif pour un webhook actif", () => {
    renderWithProviders(<WebhookRow webhook={WEBHOOK_ACTIVE} />);
    expect(screen.getByText("webhooks.active")).toBeInTheDocument();
  });

  it("affiche le badge Inactif pour un webhook inactif", () => {
    renderWithProviders(<WebhookRow webhook={WEBHOOK_INACTIVE} />);
    expect(screen.getByText("webhooks.inactive")).toBeInTheDocument();
  });

  it("affiche le bouton de menu dropdown", () => {
    renderWithProviders(<WebhookRow webhook={WEBHOOK_ACTIVE} />);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("ouvre le dropdown au clic", async () => {
    renderWithProviders(<WebhookRow webhook={WEBHOOK_ACTIVE} />);
    const trigger = screen.getByRole("button");
    fireEvent.click(trigger);
    await waitFor(() => {
      expect(screen.getByText("webhooks.test")).toBeInTheDocument();
    });
  });

  it("appelle useTestWebhook au clic sur Test", async () => {
    renderWithProviders(<WebhookRow webhook={WEBHOOK_ACTIVE} />);
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => screen.getByText("webhooks.test"));
    fireEvent.click(screen.getByText("webhooks.test"));
    await waitFor(() => expect(mockMutateAsync).toHaveBeenCalled());
  });

  it("appelle useDeleteWebhook avec confirmation", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderWithProviders(<WebhookRow webhook={WEBHOOK_ACTIVE} />);
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => screen.getByText("webhooks.delete"));
    fireEvent.click(screen.getByText("webhooks.delete"));
    await waitFor(() => expect(mockMutateAsync).toHaveBeenCalled());
    vi.restoreAllMocks();
  });

  it("n'appelle pas useDeleteWebhook si confirmation refusée", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    renderWithProviders(<WebhookRow webhook={WEBHOOK_ACTIVE} />);
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => screen.getByText("webhooks.delete"));
    fireEvent.click(screen.getByText("webhooks.delete"));
    expect(mockMutateAsync).not.toHaveBeenCalled();
    vi.restoreAllMocks();
  });
});
