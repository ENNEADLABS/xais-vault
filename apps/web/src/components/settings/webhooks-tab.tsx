"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Globe } from "lucide-react";
import { useWebhooks } from "@/lib/hooks/use-webhooks";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { WebhookRow } from "./webhook-row";
import { CreateWebhookDialog } from "./create-webhook-dialog";
import { WebhookSecretDialog } from "./webhook-secret-dialog";

export function WebhooksTab() {
  const t = useTranslations("settings");
  const { data, isLoading } = useWebhooks();
  const [createOpen, setCreateOpen] = useState(false);
  const [newSecret, setNewSecret] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  const webhooks = data?.data ?? [];

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium">{t("webhooks.title")}</h3>
          <p className="text-xs text-vault-text-muted mt-0.5">
            {t("webhooks.description")}
          </p>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          {t("webhooks.create")}
        </Button>
      </div>

      {webhooks.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center border border-vault-border rounded-lg">
          <Globe className="h-8 w-8 text-vault-text-muted mb-3" />
          <p className="text-sm font-medium">{t("webhooks.noWebhooks")}</p>
          <p className="text-xs text-vault-text-muted mt-1">
            {t("webhooks.noWebhooksHint")}
          </p>
        </div>
      ) : (
        <div className="border border-vault-border rounded-lg px-4">
          {webhooks.map((webhook) => (
            <WebhookRow key={webhook.id} webhook={webhook} />
          ))}
        </div>
      )}

      <CreateWebhookDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={(secret) => {
          setCreateOpen(false);
          setNewSecret(secret);
        }}
      />
      <WebhookSecretDialog
        secret={newSecret}
        onClose={() => setNewSecret(null)}
      />
    </div>
  );
}
