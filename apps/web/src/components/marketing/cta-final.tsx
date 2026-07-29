"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import { useFadeUp } from "@/hooks/use-fade-up";

export function CtaFinal() {
  const t = useTranslations("landing.cta");
  const [ref] = useFadeUp();

  return (
    <section className="relative py-24">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_50%,var(--color-vault-accent-dim),transparent_70%)]" />

      <div ref={ref} className="fade-up relative z-10 mx-auto max-w-3xl px-6 text-center">
        <h2 className="text-3xl font-semibold text-vault-text">
          {t("headline")}
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-vault-text-secondary">
          {t("subtitle")}
        </p>

        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Link
            href="/signup"
            className="cta-glow rounded-none bg-vault-accent px-8 py-3 font-mono text-[13px] font-medium uppercase tracking-wider text-black transition-colors hover:bg-vault-accent-hover"
          >
            {t("ctaPrimary")}
          </Link>
          <a
            href="mailto:contact@xaisoluces.com"
            className="rounded-none border border-vault-border px-8 py-3 font-mono text-[13px] font-medium uppercase tracking-wider text-vault-text-secondary transition-all hover:border-vault-accent/40 hover:text-vault-text"
          >
            {t("ctaSecondary")}
          </a>
        </div>
      </div>
    </section>
  );
}
