"use client";

import { useTranslations } from "next-intl";

interface LegalPageContentProps {
  namespace: "legal.privacy" | "legal.terms" | "legal.legal";
  sectionKeys: string[];
}

export function LegalPageContent({ namespace, sectionKeys }: LegalPageContentProps) {
  const t = useTranslations(namespace);

  return (
    <article>
      <h1 className="font-mono text-2xl font-semibold tracking-tight text-vault-text">
        {t("title")}
      </h1>
      {t.has("lastUpdated") && (
        <p className="mt-2 font-mono text-[12px] text-vault-text-muted">
          {t("lastUpdated")}
        </p>
      )}
      {t.has("intro") && (
        <p className="mt-6 text-sm leading-relaxed text-vault-text-secondary">
          {t("intro")}
        </p>
      )}

      <div className="mt-10 space-y-8">
        {sectionKeys.map((key, index) => (
          <section key={key} className="border-t border-vault-border pt-6">
            <h2 className="font-mono text-[13px] font-semibold uppercase tracking-wider text-vault-text">
              {index + 1}. {t(`sections.${key}.title`)}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-vault-text-secondary">
              {t(`sections.${key}.content`)}
            </p>
          </section>
        ))}
      </div>
    </article>
  );
}
