import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { CreateWebhookDialog } from "./create-webhook-dialog";

vi.mock("@/lib/hooks/use-webhooks", () => ({
  useCreateWebhook: vi.fn(() => ({
    mutateAsync: vi.fn().mockResolvedValue({ data: { secret: "whsec_test" } }),
    isPending: false,
  })),
}));

const defaultProps = {
  open: true,
  onOpenChange: vi.fn(),
  onCreated: vi.fn(),
};

describe("CreateWebhookDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le champ URL", () => {
    renderWithProviders(<CreateWebhookDialog {...defaultProps} />);
    expect(screen.getByLabelText("webhooks.urlLabel")).toBeInTheDocument();
  });

  it("affiche les checkboxes d'events (sans webhook.test)", () => {
    renderWithProviders(<CreateWebhookDialog {...defaultProps} />);
    expect(screen.getByText("Source ready")).toBeInTheDocument();
    expect(screen.getByText("Deliverable ready")).toBeInTheDocument();
    expect(screen.queryByText("Test")).toBeNull();
  });

  it("affiche 6 events sélectionnables", () => {
    renderWithProviders(<CreateWebhookDialog {...defaultProps} />);
    const checkboxes = screen.getAllByRole("checkbox");
    // 6 events + 1 "Active" checkbox
    expect(checkboxes).toHaveLength(7);
  });

  it("la checkbox Actif est cochée par défaut", () => {
    renderWithProviders(<CreateWebhookDialog {...defaultProps} />);
    const checkboxes = screen.getAllByRole("checkbox");
    const activeCheckbox = checkboxes[
      checkboxes.length - 1
    ] as HTMLInputElement;
    expect(activeCheckbox.checked).toBe(true);
  });

  it("permet de cocher un event", () => {
    renderWithProviders(<CreateWebhookDialog {...defaultProps} />);
    const checkboxes = screen.getAllByRole("checkbox");
    const firstEvent = checkboxes[0] as HTMLInputElement;
    expect(firstEvent.checked).toBe(false);
    fireEvent.click(firstEvent);
    expect(firstEvent.checked).toBe(true);
  });

  it("affiche le bouton de soumission", () => {
    renderWithProviders(<CreateWebhookDialog {...defaultProps} />);
    expect(screen.getByText("webhooks.createButton")).toBeInTheDocument();
  });

  it("appelle onCreated avec le secret après soumission réussie", async () => {
    const onCreated = vi.fn();
    renderWithProviders(
      <CreateWebhookDialog {...defaultProps} onCreated={onCreated} />,
    );

    // Remplir URL
    const urlInput = screen.getByLabelText("webhooks.urlLabel");
    fireEvent.change(urlInput, {
      target: { value: "https://example.com/hook" },
    });

    // Cocher un event
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]!);

    // Soumettre
    fireEvent.submit(urlInput.closest("form")!);

    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledWith("whsec_test");
    });
  });

  it("affiche une erreur si aucun event sélectionné", async () => {
    renderWithProviders(<CreateWebhookDialog {...defaultProps} />);

    const urlInput = screen.getByLabelText("webhooks.urlLabel");
    fireEvent.change(urlInput, {
      target: { value: "https://example.com/hook" },
    });
    fireEvent.submit(urlInput.closest("form")!);

    await waitFor(() => {
      // Zod validation empêche la soumission — onCreated n'est pas appelé
      expect(defaultProps.onCreated).not.toHaveBeenCalled();
    });
  });
});
