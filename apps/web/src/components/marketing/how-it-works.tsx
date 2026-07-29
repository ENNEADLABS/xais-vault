"use client";

import { useTranslations } from "next-intl";
import { useFadeUp, useFadeUpChildren } from "@/hooks/use-fade-up";

export function HowItWorks() {
  const t = useTranslations("landing.howItWorks");
  const [titleRef] = useFadeUp();
  const [stepsRef] = useFadeUpChildren();

  const steps = Array.from({ length: 3 }, (_, i) => ({
    number: String(i + 1).padStart(2, "0"),
    title: t(`steps.${i}.title`),
    description: t(`steps.${i}.description`),
  }));

  return (
    <section id="how-it-works" className="bg-vault-surface py-24">
      <div className="mx-auto max-w-5xl px-6">
        <div ref={titleRef} className="fade-up mb-16 text-center">
          <span className="font-mono text-[13px] uppercase tracking-widest text-vault-accent">
            {t("label")}
          </span>
          <h2 className="mt-3 text-3xl font-semibold text-vault-text">
            {t("title")}
          </h2>
        </div>

        <div ref={stepsRef} className="grid grid-cols-1 gap-12 md:grid-cols-3">
          {steps.map((step, i) => (
            <div key={step.number} className={`fade-up stagger-${i + 1} relative text-center`}>
              <div className="font-mono text-5xl font-semibold text-vault-accent/20">
                {step.number}
              </div>
              <h3 className="mt-4 text-xl font-semibold text-vault-text">
                {step.title}
              </h3>
              <p className="mt-2 text-vault-text-secondary">
                {step.description}
              </p>
              {/* Ligne connectrice animée */}
              {i < 2 && (
                <div className="absolute right-0 top-6 hidden h-px w-12 translate-x-full overflow-hidden md:block">
                  <div className="step-line h-full bg-linear-to-r from-vault-accent/40 to-vault-accent/10 visible" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
