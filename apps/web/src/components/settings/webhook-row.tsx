"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { MoreHorizontal } from "lucide-react";
import {
  useUpdateWebhook,
  useDeleteWebhook,
  useTestWebhook,
  useRotateWebhookSecret,
} from "@/lib/hooks/use-webhooks";
import type { Webhook } from "@/types/api";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { WebhookDeliveriesDialog } from "./webhook-deliveries-dialog";
import { WebhookSecretDialog } from "./webhook-secret-dialog";

const EVENT_LABELS: Record<string, string> = {
  "source.ready": "Source ready",
  "source.failed": "Source failed",
  "scan.completed": "Scan completed",
  "insight.created": "Insight created",
  "investigation.completed": "Investigation completed",
  "deliverable.ready": "Deliverable ready",
  "webhook.test": "Test",
};

interface WebhookRowProps {
  webhook: Webhook;
}

export function WebhookRow({ webhook }: WebhookRowProps) {
  const t = useTranslations("settings");
  const [deliveriesOpen, setDeliveriesOpen] = useState(false);
  const [rotatedSecret, setRotatedSecret] = useState<string | null>(null);

  const updateWebhook = useUpdateWebhook(webhook.id);
  const deleteWebhook = useDeleteWebhook();
  const testWebhook = useTestWebhook();
  const rotateSecret = useRotateWebhookSecret();

  async function handleTest() {
    try {
      await testWebhook.mutateAsync(webhook.id);
      toast.success(t("webhooks.testSent"));
    } catch {
      toast.error("Erreur lors du test");
    }
  }

  async function handleRotate() {
    if (!confirm(t("webhooks.rotateConfirm"))) return;
    try {
      const result = await rotateSecret.mutateAsync(webhook.id);
      if (result.data?.secret) setRotatedSecret(result.data.secret);
    } catch {
      toast.error("Erreur lors de la rotation");
    }
  }

  async function handleDelete() {
    if (!confirm(t("webhooks.deleteConfirm"))) return;
    try {
      await deleteWebhook.mutateAsync(webhook.id);
      toast.success(t("webhooks.deleted"));
    } catch {
      toast.error("Erreur lors de la suppression");
    }
  }

  async function handleToggleActive() {
    try {
      await updateWebhook.mutateAsync({ is_active: !webhook.is_active });
    } catch {
      toast.error("Erreur lors de la mise à jour");
    }
  }

  return (
    <>
      <div className="flex items-center justify-between py-3 border-b last:border-0">
        <div className="space-y-1 min-w-0 flex-1 mr-3">
          <p className="text-sm font-medium truncate max-w-xs">{webhook.url}</p>
          <div className="flex flex-wrap gap-1">
            {webhook.events.map((e) => (
              <span key={e} className="rounded bg-vault-border/30 px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide text-vault-text-secondary">
                {EVENT_LABELS[e] ?? e}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={cn("rounded px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide", webhook.is_active ? "bg-vault-success-dim text-vault-success" : "bg-vault-border/40 text-vault-text-muted")}>
            {webhook.is_active ? t("webhooks.active") : t("webhooks.inactive")}
          </span>
          <DropdownMenu>
            <DropdownMenuTrigger className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring">
              <MoreHorizontal className="h-4 w-4" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleTest}>
                {t("webhooks.test")}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setDeliveriesOpen(true)}>
                {t("webhooks.deliveries")}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleToggleActive}>
                {webhook.is_active
                  ? t("webhooks.inactive")
                  : t("webhooks.active")}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleRotate}>
                {t("webhooks.rotateSecret")}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={handleDelete}
                className="text-destructive focus:text-destructive"
              >
                {t("webhooks.delete")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <WebhookDeliveriesDialog
        webhookId={webhook.id}
        open={deliveriesOpen}
        onOpenChange={setDeliveriesOpen}
      />
      <WebhookSecretDialog
        secret={rotatedSecret}
        onClose={() => setRotatedSecret(null)}
      />
    </>
  );
}
