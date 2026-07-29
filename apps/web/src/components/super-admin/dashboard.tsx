"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { Shield } from "lucide-react";
import { useSuperAdminCheck } from "@/lib/hooks/use-super-admin";
import { OverviewCards } from "./overview-cards";
import { ActivityFeed } from "./activity-feed";
import { HealthPanel } from "./health-panel";
import { SummarizationPanel } from "./summarization-panel";
import { cn } from "@/lib/utils";

type Tab = "activity" | "health" | "summarization" | "overview";

export function SuperAdminDashboard() {
  const t = useTranslations("superAdmin");
  const { data, isLoading } = useSuperAdminCheck();
  const [activeTab, setActiveTab] = useState<Tab>("activity");
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");

  const handleOrgClick = useCallback((orgId: string) => {
    setSelectedOrgId(orgId);
    setActiveTab("activity");
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 text-vault-text-muted">
        {t("loading")}
      </div>
    );
  }

  if (!data?.is_super_admin) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3">
        <Shield className="h-10 w-10 text-vault-text-muted" />
        <p className="text-vault-text-muted font-mono text-sm">{t("accessDenied")}</p>
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "activity", label: t("tabs.activity") },
    { key: "health", label: t("tabs.health") },
    { key: "summarization", label: t("tabs.summarization") },
    { key: "overview", label: t("tabs.overview") },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Shield className="h-5 w-5 text-vault-accent" />
        <h1 className="font-mono text-lg font-semibold tracking-tight text-vault-text">
          {t("title")}
        </h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-vault-border">
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={cn(
              "px-4 py-2 font-mono text-xs uppercase tracking-wider transition-colors",
              activeTab === key
                ? "border-b-2 border-vault-accent text-vault-text"
                : "text-vault-text-muted hover:text-vault-text-secondary",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === "activity" && <ActivityFeed initialOrgId={selectedOrgId} />}
      {activeTab === "health" && <HealthPanel />}
      {activeTab === "summarization" && <SummarizationPanel />}
      {activeTab === "overview" && <OverviewCards onOrgClick={handleOrgClick} />}
    </div>
  );
}
