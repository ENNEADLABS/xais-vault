"use client";

import { useTranslations } from "next-intl";
import React from "react";
import {
  FileSearch, MessageSquare, ShieldAlert, FileStack, FileText, Users,
} from "lucide-react";
import { useFadeUp, useFadeUpChildren } from "@/hooks/use-fade-up";

/* Icône + couleur accent distincte par feature */
const FEATURES = [
  { Icon: FileSearch, color: "text-cyan-400", bg: "bg-cyan-400/10" },
  { Icon: MessageSquare, color: "text-emerald-400", bg: "bg-emerald-400/10" },
  { Icon: ShieldAlert, color: "text-red-400", bg: "bg-red-400/10" },
  { Icon: FileStack, color: "text-amber-400", bg: "bg-amber-400/10" },
  { Icon: FileText, color: "text-blue-400", bg: "bg-blue-400/10" },
  { Icon: Users, color: "text-violet-400", bg: "bg-violet-400/10" },
];

export function FeaturesGrid() {
  const t = useTranslations("landing.features");
  const [titleRef] = useFadeUp();
  const [gridRef] = useFadeUpChildren();

  const features = FEATURES.map((f, i) => ({
    ...f,
    title: t(`items.${i}.title`),
    description: t(`items.${i}.description`),
  }));

  return (
    <section id="features" className="py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div ref={titleRef} className="fade-up mb-12 text-center">
          <span className="font-mono text-[13px] uppercase tracking-widest text-vault-accent">
            {t("label")}
          </span>
          <h2 className="mt-3 text-3xl font-semibold text-vault-text">
            {t("title")}
          </h2>
        </div>

        <div
          ref={gridRef}
          className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3"
        >
          {features.map((feature, i) => (
            <div
              key={feature.title}
              className={`fade-up stagger-${i + 1} group rounded-lg border border-vault-border bg-vault-surface p-6 transition-[border-color,transform,box-shadow] duration-300 hover:border-vault-border-active hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20`}
            >
              <div className={`mb-4 flex h-10 w-10 items-center justify-center rounded-lg ${feature.bg}`}>
                <feature.Icon className={`h-5 w-5 ${feature.color}`} />
              </div>
              <h3 className="text-lg font-semibold text-vault-text">
                {feature.title}
              </h3>
              <p className="mt-2 text-[14px] leading-relaxed text-vault-text-secondary">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
