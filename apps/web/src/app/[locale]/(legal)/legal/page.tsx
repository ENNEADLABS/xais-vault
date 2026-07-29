import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { LegalPageContent } from "@/components/legal/legal-page-content";

const SECTION_KEYS = [
  "editor",
  "hosting",
  "intellectualProperty",
  "personalData",
  "cookies",
  "contact",
];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "legal.legal" });
  return { title: `${t("title")} — XAIS Vault` };
}

export default async function LegalNoticePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <LegalPageContent namespace="legal.legal" sectionKeys={SECTION_KEYS} />;
}
