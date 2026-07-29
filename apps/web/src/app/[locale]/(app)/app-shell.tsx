"use client";

import { useTranslations } from "next-intl";
import { useEnsureOrganization } from "@/hooks/use-ensure-organization";
import { UpgradeBanner } from "@/components/layout/upgrade-banner";

export function AppShell({ children }: { children: React.ReactNode }) {
  const t = useTranslations("common");
  const { isLoading } = useEnsureOrganization();

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground text-sm">{t("loading")}</p>
      </div>
    );
  }

  return (
    <>
      <UpgradeBanner />
      {children}
    </>
  );
}
