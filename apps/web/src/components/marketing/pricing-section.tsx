"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { Check } from "lucide-react";
import { useFadeUp } from "@/hooks/use-fade-up";
import { cn } from "@/lib/utils";
import type { BillingInterval } from "@/lib/constants/billing";

interface PlanProps {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  cta: string;
  href: string;
  highlighted?: boolean;
}

function PlanCard({ name, price, period, description, features, cta, href, highlighted }: PlanProps) {
  return (
    <div
      className={cn(
        "relative flex flex-col rounded-lg border p-6 transition-all duration-200",
        highlighted
          ? "border-vault-accent bg-vault-accent/[0.03] shadow-[0_0_30px_rgba(6,182,212,0.08)]"
          : "border-vault-border bg-vault-surface hover:border-vault-border-active",
      )}
    >
      {highlighted && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 font-mono text-[11px] uppercase tracking-widest text-vault-accent bg-vault-bg px-3 py-0.5 border border-vault-accent rounded-full">
          Popular
        </span>
      )}
      <div className="mb-6">
        <h3 className="font-mono text-[13px] font-semibold uppercase tracking-wider text-vault-text">
          {name}
        </h3>
        <div className="mt-3 flex items-baseline gap-1">
          <span className="text-3xl font-semibold text-vault-text">{price}</span>
          {period && <span className="text-sm text-vault-text-muted">{period}</span>}
        </div>
        <p className="mt-2 text-sm text-vault-text-secondary">{description}</p>
      </div>

      <ul className="mb-8 flex-1 space-y-2.5">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-vault-text-secondary">
            <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-vault-accent" />
            {f}
          </li>
        ))}
      </ul>

      <Link
        href={href}
        className={cn(
          "block w-full py-2.5 text-center font-mono text-[12px] font-medium uppercase tracking-wider transition-colors",
          highlighted
            ? "bg-vault-accent text-black hover:bg-vault-accent-hover"
            : "border border-vault-border text-vault-text-secondary hover:border-vault-accent/40 hover:text-vault-text",
        )}
      >
        {cta}
      </Link>
    </div>
  );
}

interface IntervalToggleProps {
  interval: BillingInterval;
  onToggle: (interval: BillingInterval) => void;
  monthlyLabel: string;
  yearlyLabel: string;
  discountLabel: string;
}

function IntervalToggle({ interval, onToggle, monthlyLabel, yearlyLabel, discountLabel }: IntervalToggleProps) {
  return (
    <div className="mt-6 flex items-center justify-center gap-3">
      <button
        type="button"
        onClick={() => onToggle("monthly")}
        className={cn(
          "font-mono text-[12px] uppercase tracking-wider px-4 py-1.5 rounded-full transition-colors",
          interval === "monthly"
            ? "bg-vault-accent/10 text-vault-accent border border-vault-accent/30"
            : "text-vault-text-muted hover:text-vault-text-secondary",
        )}
      >
        {monthlyLabel}
      </button>
      <button
        type="button"
        onClick={() => onToggle("yearly")}
        className={cn(
          "font-mono text-[12px] uppercase tracking-wider px-4 py-1.5 rounded-full transition-colors inline-flex items-center gap-2",
          interval === "yearly"
            ? "bg-vault-accent/10 text-vault-accent border border-vault-accent/30"
            : "text-vault-text-muted hover:text-vault-text-secondary",
        )}
      >
        {yearlyLabel}
        <span className="text-[10px] font-medium text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full">
          {discountLabel}
        </span>
      </button>
    </div>
  );
}

export function PricingSection() {
  const t = useTranslations("landing.pricing");
  const [ref] = useFadeUp();
  const [interval, setInterval] = useState<BillingInterval>("monthly");

  const isYearly = interval === "yearly";

  const plans: PlanProps[] = [
    {
      name: t("starter.name"),
      price: isYearly ? t("starter.priceYearly") : t("starter.price"),
      period: isYearly ? t("perYear") : t("perMonth"),
      description: t("starter.description"),
      features: [
        t("starter.f1"),
        t("starter.f2"),
        t("starter.f3"),
        t("starter.f4"),
      ],
      cta: t("starter.cta"),
      href: `/signup?plan=starter&interval=${interval}`,
    },
    {
      name: t("premium.name"),
      price: isYearly ? t("premium.priceYearly") : t("premium.price"),
      period: isYearly ? t("perYear") : t("perMonth"),
      description: t("premium.description"),
      features: [
        t("premium.f1"),
        t("premium.f2"),
        t("premium.f3"),
        t("premium.f4"),
        t("premium.f5"),
      ],
      cta: t("premium.cta"),
      href: `/signup?plan=premium&interval=${interval}`,
      highlighted: true,
    },
    {
      name: t("team.name"),
      price: isYearly ? t("team.priceYearly") : t("team.price"),
      period: isYearly ? t("perYear") : t("perMonth"),
      description: t("team.description"),
      features: [
        t("team.f1"),
        t("team.f2"),
        t("team.f3"),
        t("team.f4"),
        t("team.f5"),
      ],
      cta: t("team.cta"),
      href: `/signup?plan=team&interval=${interval}`,
    },
    {
      name: t("enterprise.name"),
      price: t("enterprise.price"),
      period: "",
      description: t("enterprise.description"),
      features: [
        t("enterprise.f1"),
        t("enterprise.f2"),
        t("enterprise.f3"),
        t("enterprise.f4"),
        t("enterprise.f5"),
      ],
      cta: t("enterprise.cta"),
      href: "mailto:contact@xaisoluces.com",
    },
  ];

  return (
    <section id="pricing" className="py-24">
      <div ref={ref} className="fade-up mx-auto max-w-6xl px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="font-mono text-[12px] uppercase tracking-widest text-vault-accent">
            {t("label")}
          </p>
          <h2 className="mt-3 text-3xl font-semibold text-vault-text">
            {t("title")}
          </h2>
          <IntervalToggle
            interval={interval}
            onToggle={setInterval}
            monthlyLabel={t("monthly")}
            yearlyLabel={t("yearly")}
            discountLabel={t("yearlyDiscount")}
          />
        </div>

        <div className="mt-16 grid gap-6 md:grid-cols-4">
          {plans.map((plan) => (
            <PlanCard key={plan.name} {...plan} />
          ))}
        </div>
      </div>
    </section>
  );
}
