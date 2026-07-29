import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/tests/render";
import { LegalPageContent } from "./legal-page-content";

vi.mock("next-intl", () => ({
  useTranslations: (namespace: string) => {
    const data: Record<string, Record<string, string>> = {
      "legal.privacy": {
        title: "Politique de confidentialité",
        lastUpdated: "Dernière mise à jour : 20 mars 2026",
        intro: "Intro confidentialité",
        "sections.dataController.title": "Responsable du traitement",
        "sections.dataController.content": "XAIS SOLUCES, Saint-Raphaël",
        "sections.contact.title": "Contact",
        "sections.contact.content": "contact@xaisoluces.com",
      },
      "legal.legal": {
        title: "Mentions légales",
        lastUpdated: "Dernière mise à jour : 20 mars 2026",
        "sections.editor.title": "Éditeur",
        "sections.editor.content": "XAIS SOLUCES",
      },
    };

    const translations = data[namespace] ?? {};

    const t = (key: string) => translations[key] ?? key;
    t.has = (key: string) => key in translations;
    return t;
  },
}));

describe("LegalPageContent", () => {
  it("affiche le titre de la page", () => {
    renderWithProviders(
      <LegalPageContent
        namespace="legal.privacy"
        sectionKeys={["dataController"]}
      />
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Politique de confidentialité"
    );
  });

  it("affiche la date de mise à jour", () => {
    renderWithProviders(
      <LegalPageContent
        namespace="legal.privacy"
        sectionKeys={["dataController"]}
      />
    );
    expect(screen.getByText("Dernière mise à jour : 20 mars 2026")).toBeInTheDocument();
  });

  it("affiche l'intro quand elle est présente", () => {
    renderWithProviders(
      <LegalPageContent
        namespace="legal.privacy"
        sectionKeys={["dataController"]}
      />
    );
    expect(screen.getByText("Intro confidentialité")).toBeInTheDocument();
  });

  it("n'affiche pas l'intro si elle est absente", () => {
    renderWithProviders(
      <LegalPageContent
        namespace="legal.legal"
        sectionKeys={["editor"]}
      />
    );
    expect(screen.queryByText("Intro confidentialité")).not.toBeInTheDocument();
  });

  it("numérote les sections à partir de 1", () => {
    renderWithProviders(
      <LegalPageContent
        namespace="legal.privacy"
        sectionKeys={["dataController", "contact"]}
      />
    );

    const headings = screen.getAllByRole("heading", { level: 2 });
    expect(headings[0]).toHaveTextContent("1. Responsable du traitement");
    expect(headings[1]).toHaveTextContent("2. Contact");
  });

  it("affiche le contenu de chaque section", () => {
    renderWithProviders(
      <LegalPageContent
        namespace="legal.privacy"
        sectionKeys={["dataController"]}
      />
    );
    expect(screen.getByText("XAIS SOLUCES, Saint-Raphaël")).toBeInTheDocument();
  });

  it("rend autant de sections que de clés fournies", () => {
    renderWithProviders(
      <LegalPageContent
        namespace="legal.privacy"
        sectionKeys={["dataController", "contact"]}
      />
    );
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(2);
  });
});
