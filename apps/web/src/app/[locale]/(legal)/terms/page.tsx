import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { LegalPageContent } from "@/components/legal/legal-page-content";

const SECTION_KEYS = [
  "definitions",
  "object",
  "access",
  "subscriptions",
  "obligations",
  "intellectualProperty",
  "liability",
  "termination",
  "applicableLaw",
];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "legal.terms" });
  return { title: `${t("title")} — XAIS Vault` };
}

export default async function TermsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <LegalPageContent namespace="legal.terms" sectionKeys={SECTION_KEYS} />;
}
