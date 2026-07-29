"use client";

import { useTranslations } from "next-intl";
import { useFadeUpChildren } from "@/hooks/use-fade-up";

export function SocialProofBar() {
  const t = useTranslations("landing.metrics");
  const [containerRef] = useFadeUpChildren();

  const metrics = [
    { value: t("docsValue"), label: t("docsLabel") },
    { value: t("timeValue"), label: t("timeLabel") },
    { value: t("accuracyValue"), label: t("accuracyLabel") },
    { value: t("cycleValue"), label: t("cycleLabel") },
  ];

  return (
    <section className="border-y border-vault-border bg-vault-surface py-12">
      <div
        ref={containerRef}
        className="mx-auto grid max-w-5xl grid-cols-2 gap-8 px-6 md:grid-cols-4"
      >
        {metrics.map((metric, i) => (
          <div key={metric.label} className={`fade-up stagger-${i + 1} text-center`}>
            <div className="font-mono text-3xl font-semibold text-vault-accent">
              {metric.value}
            </div>
            <div className="mt-1 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
              {metric.label}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
