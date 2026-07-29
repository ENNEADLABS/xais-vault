"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useCreateWebhook } from "@/lib/hooks/use-webhooks";
import { WEBHOOK_EVENTS } from "@/types/api";
import { createWebhookSchema, type CreateWebhookFormData } from "@/lib/schemas/settings";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const EVENT_LABELS: Record<string, string> = {
  "source.ready": "Source ready",
  "source.failed": "Source failed",
  "scan.completed": "Scan completed",
  "insight.created": "Insight created",
  "investigation.completed": "Investigation completed",
  "deliverable.ready": "Deliverable ready",
};

const SELECTABLE_EVENTS = WEBHOOK_EVENTS.filter((e) => e !== "webhook.test");

interface CreateWebhookDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (secret: string) => void;
}

export function CreateWebhookDialog({
  open,
  onOpenChange,
  onCreated,
}: CreateWebhookDialogProps) {
  const t = useTranslations("settings");
  const createWebhook = useCreateWebhook();

  const { register, handleSubmit, control, reset, formState: { errors } } =
    useForm<CreateWebhookFormData>({
      resolver: zodResolver(createWebhookSchema),
      defaultValues: { url: "", events: [], isActive: true },
    });

  async function onSubmit(data: CreateWebhookFormData) {
    try {
      const result = await createWebhook.mutateAsync({
        url: data.url,
        events: data.events,
        is_active: data.isActive,
      });
      if (result.data?.secret) {
        reset();
        onOpenChange(false);
        onCreated(result.data.secret);
      }
    } catch {
      toast.error("Erreur lors de la création");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("webhooks.create")}</DialogTitle>
          <DialogDescription>{t("webhooks.description")}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="webhook-url">{t("webhooks.urlLabel")}</Label>
            <Input
              id="webhook-url"
              type="url"
              placeholder={t("webhooks.urlPlaceholder")}
              {...register("url")}
            />
            {errors.url && (
              <p className="text-xs text-vault-danger">{errors.url.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label>{t("webhooks.eventsLabel")}</Label>
            <Controller
              name="events"
              control={control}
              render={({ field }) => (
                <div className="space-y-2 rounded-md border p-3">
                  {SELECTABLE_EVENTS.map((event) => (
                    <label
                      key={event}
                      className="flex items-center gap-2 cursor-pointer select-none"
                    >
                      <input
                        type="checkbox"
                        checked={field.value.includes(event)}
                        onChange={(e) => {
                          const next = e.target.checked
                            ? [...field.value, event]
                            : field.value.filter((v) => v !== event);
                          field.onChange(next);
                        }}
                        className="h-4 w-4 rounded border"
                      />
                      <span className="text-sm">{EVENT_LABELS[event] ?? event}</span>
                    </label>
                  ))}
                </div>
              )}
            />
            {errors.events && (
              <p className="text-xs text-vault-danger">{errors.events.message}</p>
            )}
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              {...register("isActive")}
              className="h-4 w-4 rounded border"
            />
            <span className="text-sm">{t("webhooks.activeLabel")}</span>
          </label>

          <DialogFooter>
            <Button type="submit" disabled={createWebhook.isPending}>
              {createWebhook.isPending
                ? t("webhooks.creating")
                : t("webhooks.createButton")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
