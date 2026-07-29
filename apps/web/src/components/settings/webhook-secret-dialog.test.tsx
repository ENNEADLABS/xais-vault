import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { WebhookSecretDialog } from "./webhook-secret-dialog";

const SECRET = "whsec_test_placeholder_value_not_a_real_secret";

describe("WebhookSecretDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("ne rend rien quand secret est null", () => {
    renderWithProviders(
      <WebhookSecretDialog secret={null} onClose={vi.fn()} />,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("affiche le dialog quand secret est présent", () => {
    renderWithProviders(
      <WebhookSecretDialog secret={SECRET} onClose={vi.fn()} />,
    );
    expect(screen.getByDisplayValue(SECRET)).toBeInTheDocument();
  });

  it("affiche le secret dans un input en lecture seule", () => {
    renderWithProviders(
      <WebhookSecretDialog secret={SECRET} onClose={vi.fn()} />,
    );
    const input = screen.getByDisplayValue(SECRET) as HTMLInputElement;
    expect(input.readOnly).toBe(true);
  });

  it("le bouton Done est désactivé tant que le secret n'est pas copié", () => {
    renderWithProviders(
      <WebhookSecretDialog secret={SECRET} onClose={vi.fn()} />,
    );
    const doneBtn = screen.getByText("webhooks.done");
    expect(doneBtn).toBeDisabled();
  });

  it("copie le secret dans le clipboard au clic sur Copier", async () => {
    renderWithProviders(
      <WebhookSecretDialog secret={SECRET} onClose={vi.fn()} />,
    );
    // Le bouton Copy est icon-only — on le trouve via aria-label
    const copyBtn = screen.getByRole("button", { name: "copy" });
    fireEvent.click(copyBtn);
    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(SECRET);
    });
  });

  it("active le bouton Done après la copie", async () => {
    renderWithProviders(
      <WebhookSecretDialog secret={SECRET} onClose={vi.fn()} />,
    );
    const copyBtn = screen.getByRole("button", { name: "copy" });
    fireEvent.click(copyBtn);
    await waitFor(() => {
      expect(screen.getByText("webhooks.done")).not.toBeDisabled();
    });
  });

  it("appelle onClose quand Done est cliqué après copie", async () => {
    const onClose = vi.fn();
    renderWithProviders(
      <WebhookSecretDialog secret={SECRET} onClose={onClose} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "copy" }));
    await waitFor(() =>
      expect(screen.getByText("webhooks.done")).not.toBeDisabled(),
    );
    fireEvent.click(screen.getByText("webhooks.done"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
