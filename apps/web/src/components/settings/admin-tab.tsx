"use client";

import { useTranslations } from "next-intl";
import { OrgOverview } from "./admin/org-overview";
import { UsageChart } from "./admin/usage-chart";
import { CostBreakdown } from "./admin/cost-breakdown";
import { ActivityLog } from "./admin/activity-log";
import { ApiKeyUsage } from "./admin/api-key-usage";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h3 className="font-mono text-[11px] uppercase tracking-widest text-vault-text-muted border-b border-vault-border pb-2">
        {title}
      </h3>
      {children}
    </div>
  );
}

export function AdminTab() {
  const t = useTranslations("settings.admin");

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-base font-semibold text-vault-text mb-1">{t("title")}</h2>
        <p className="text-sm text-vault-text-muted">{t("description")}</p>
      </div>

      <Section title={t("overviewSection")}>
        <OrgOverview />
      </Section>

      <Section title={t("usageSection")}>
        <UsageChart />
      </Section>

      <Section title={t("costsSection")}>
        <CostBreakdown />
      </Section>

      <Section title={t("activitySection")}>
        <ActivityLog />
      </Section>

      <Section title={t("apiKeysSection")}>
        <ApiKeyUsage />
      </Section>
    </div>
  );
}
