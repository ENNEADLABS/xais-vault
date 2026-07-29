"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useUIStore } from "@/stores/ui-store";
import { ProfileTab } from "./profile-tab";
import { OrganizationTab } from "./organization-tab";
import { DangerZoneTab } from "./danger-zone-tab";
import { ApiKeysTab } from "./api-keys-tab";
import { BillingSection } from "./billing-section";
import { WebhooksTab } from "./webhooks-tab";
import { AdminTab } from "./admin-tab";
import { useCurrentOrgRole } from "@/lib/hooks/use-organization";
import { cn } from "@/lib/utils";

type TabId = "profile" | "organization" | "billing" | "api-keys" | "webhooks" | "admin" | "danger";

export function SettingsTabs() {
  const t = useTranslations("settings");
  const organizationId = useUIStore((s) => s.organizationId);
  const [active, setActive] = useState<TabId>("profile");
  const currentRole = useCurrentOrgRole(organizationId ?? "");
  const isAdmin = currentRole === "admin";

  const mainTabs: { id: TabId; label: string }[] = [
    { id: "profile", label: t("tabs.profile") },
    { id: "organization", label: t("tabs.organization") },
    { id: "billing", label: t("tabs.billing") },
    { id: "api-keys", label: t("tabs.apiKeys") },
    { id: "webhooks", label: t("tabs.webhooks") },
    ...(isAdmin ? [{ id: "admin" as const, label: t("tabs.admin") }] : []),
  ];

  return (
    <div className="flex w-full min-h-0 flex-1">
      {/* Panneau gauche — nav verticale */}
      <div className="w-50 shrink-0 border-r border-vault-border bg-vault-bg flex flex-col py-6">
        <p className="px-4 pb-3 font-mono text-[11px] uppercase tracking-widest text-vault-text-muted">
          {t("title")}
        </p>

        <nav className="flex-1 space-y-0.5 px-2">
          {mainTabs.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActive(id)}
              className={cn(
                "w-full text-left px-3 py-2 rounded-md text-[13px] transition-colors duration-150",
                active === id
                  ? "bg-vault-surface text-vault-text font-medium"
                  : "text-vault-text-muted hover:text-vault-text-secondary",
              )}
            >
              {label}
            </button>
          ))}
        </nav>

        {/* Zone danger — séparée */}
        <div className="border-t border-vault-border mt-4 pt-4 px-2">
          <button
            type="button"
            onClick={() => setActive("danger")}
            className={cn(
              "w-full text-left px-3 py-2 rounded-md text-[13px] transition-colors duration-150",
              active === "danger"
                ? "bg-vault-danger/10 text-vault-danger font-medium"
                : "text-vault-danger/60 hover:text-vault-danger",
            )}
          >
            {t("tabs.danger")}
          </button>
        </div>
      </div>

      {/* Panneau droit — contenu */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-150">
          {active === "profile" && <ProfileTab />}

          {active === "organization" && (
            organizationId
              ? <OrganizationTab orgId={organizationId} />
              : <p className="text-vault-text-muted text-sm">Aucune organisation sélectionnée.</p>
          )}

          {active === "billing" && (
            organizationId
              ? <BillingSection />
              : <p className="text-vault-text-muted text-sm">Aucune organisation sélectionnée.</p>
          )}

          {active === "api-keys" && (
            organizationId
              ? <ApiKeysTab orgId={organizationId} />
              : <p className="text-vault-text-muted text-sm">Aucune organisation sélectionnée.</p>
          )}

          {active === "webhooks" && (
            organizationId
              ? <WebhooksTab orgId={organizationId} />
              : <p className="text-vault-text-muted text-sm">Aucune organisation sélectionnée.</p>
          )}

          {active === "admin" && (
            organizationId
              ? <AdminTab />
              : <p className="text-vault-text-muted text-sm">Aucune organisation sélectionnée.</p>
          )}

          {active === "danger" && (
            organizationId
              ? <DangerZoneTab orgId={organizationId} />
              : <p className="text-vault-text-muted text-sm">Aucune organisation sélectionnée.</p>
          )}
        </div>
      </div>
    </div>
  );
}
