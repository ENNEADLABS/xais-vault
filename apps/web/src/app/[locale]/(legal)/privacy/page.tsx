import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { LegalPageContent } from "@/components/legal/legal-page-content";

const SECTION_KEYS = [
  "dataController",
  "dataCollected",
  "purpose",
  "legalBasis",
  "retention",
  "thirdParties",
  "rights",
  "cookies",
  "contact",
];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "legal.privacy" });
  return { title: `${t("title")} — XAIS Vault` };
}

export default async function PrivacyPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <LegalPageContent namespace="legal.privacy" sectionKeys={SECTION_KEYS} />;
}
