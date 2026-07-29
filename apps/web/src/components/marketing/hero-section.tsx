"use client";

import { useTranslations } from "next-intl";
import Image from "next/image";
import Link from "next/link";
import { useFadeUp } from "@/hooks/use-fade-up";

export function HeroSection() {
  const t = useTranslations("landing.hero");
  const [textRef] = useFadeUp();
  const [screenshotRef] = useFadeUp();

  return (
    <section className="relative flex min-h-[90vh] flex-col items-center justify-center overflow-hidden px-6 pt-16">
      {/* Gradient radial plus visible */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,var(--color-vault-accent-dim),transparent_70%)]" />

      <div ref={textRef} className="fade-up relative z-10 mx-auto max-w-4xl text-center">
        <h1 className="text-4xl font-semibold leading-tight tracking-tight text-vault-text md:text-6xl">
          {t("headline")}
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-vault-text-secondary">
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
            href="#how-it-works"
            className="rounded-none border border-vault-border px-8 py-3 font-mono text-[13px] font-medium uppercase tracking-wider text-vault-text-secondary transition-all hover:border-vault-accent/40 hover:text-vault-text"
          >
            {t("ctaSecondary")}
          </a>
        </div>
      </div>

      {/* Screenshot avec perspective 3D + glow */}
      <div ref={screenshotRef} className="fade-up relative z-10 mx-auto mt-16 max-w-5xl perspective-distant">
        <div
          className="rounded-lg border border-vault-border shadow-2xl shadow-cyan-500/10 transition-transform duration-500 transform-[rotateX(2deg)] hover:transform-[rotateX(0deg)]"
        >
          {/* Glow derrière le screenshot */}
          <div className="absolute -inset-px -z-10 rounded-lg bg-linear-to-b from-vault-accent/20 via-transparent to-transparent blur-xl" />
          <Image
            src="/images/product-screenshot.png"
            alt="XAIS Vault workspace analysis"
            width={1200}
            height={750}
            className="rounded-lg"
            priority
          />
        </div>
      </div>
    </section>
  );
}
