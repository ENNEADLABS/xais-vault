"use client";

import { useTranslations } from "next-intl";
import { useWebhookDeliveries } from "@/lib/hooks/use-webhooks";
import type { WebhookDelivery } from "@/types/api";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface WebhookDeliveriesDialogProps {
  webhookId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const STATUS_CLASSES: Record<WebhookDelivery["status"], string> = {
  delivered: "bg-vault-success-dim text-vault-success",
  failed: "bg-red-500/10 text-red-400",
  pending: "bg-vault-border/40 text-vault-text-muted",
};

function StatusBadge({ status }: { status: WebhookDelivery["status"] }) {
  const t = useTranslations("settings");
  return (
    <span className={cn("rounded px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide", STATUS_CLASSES[status])}>
      {t(
        `webhooks.status${status.charAt(0).toUpperCase() + status.slice(1)}` as Parameters<
          typeof t
        >[0],
      )}
    </span>
  );
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

export function WebhookDeliveriesDialog({
  webhookId,
  open,
  onOpenChange,
}: WebhookDeliveriesDialogProps) {
  const t = useTranslations("settings");
  const { data, isLoading } = useWebhookDeliveries(webhookId);
  const deliveries = data?.data ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("webhooks.deliveriesTitle")}</DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : deliveries.length === 0 ? (
          <p className="text-sm text-vault-text-muted py-4 text-center">
            {t("webhooks.deliveriesEmpty")}
          </p>
        ) : (
          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead className="border-b">
                <tr className="text-left text-vault-text-muted">
                  <th className="pb-2 font-medium pr-4">
                    {t("webhooks.deliveryEvent")}
                  </th>
                  <th className="pb-2 font-medium pr-4">
                    {t("webhooks.deliveryStatus")}
                  </th>
                  <th className="pb-2 font-medium pr-4">
                    {t("webhooks.deliveryHttpStatus")}
                  </th>
                  <th className="pb-2 font-medium pr-4">
                    {t("webhooks.deliveryAttempt")}
                  </th>
                  <th className="pb-2 font-medium">
                    {t("webhooks.deliveryDate")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {deliveries.map((delivery) => (
                  <tr key={delivery.id} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-mono text-xs">
                      {delivery.event_type}
                    </td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={delivery.status} />
                    </td>
                    <td className="py-2 pr-4 text-vault-text-muted">
                      {delivery.http_status ?? "—"}
                    </td>
                    <td className="py-2 pr-4 text-vault-text-muted">
                      {delivery.attempt}
                    </td>
                    <td className="py-2 text-vault-text-muted text-xs">
                      {formatDate(delivery.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
