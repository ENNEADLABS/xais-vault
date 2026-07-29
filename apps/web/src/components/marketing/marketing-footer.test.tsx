import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { MarketingFooter } from "./marketing-footer";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock("@/components/ui/vault-logo", () => ({
  VaultLogo: () => <span>VaultLogo</span>,
}));

describe("MarketingFooter — liens légaux", () => {
  it("le lien confidentialité pointe vers /privacy", () => {
    renderWithProviders(<MarketingFooter />);
    const link = screen.getByText("privacy");
    expect(link.closest("a")).toHaveAttribute("href", "/privacy");
  });

  it("le lien CGU pointe vers /terms", () => {
    renderWithProviders(<MarketingFooter />);
    const link = screen.getByText("terms");
    expect(link.closest("a")).toHaveAttribute("href", "/terms");
  });

  it("le lien mentions légales pointe vers /legal", () => {
    renderWithProviders(<MarketingFooter />);
    const link = screen.getByText("legal");
    expect(link.closest("a")).toHaveAttribute("href", "/legal");
  });

  it("aucun lien légal ne pointe vers #", () => {
    renderWithProviders(<MarketingFooter />);
    const links = screen.getAllByRole("link");
    const hashLinks = links.filter((l) => l.getAttribute("href") === "#");
    expect(hashLinks).toHaveLength(0);
  });
});
