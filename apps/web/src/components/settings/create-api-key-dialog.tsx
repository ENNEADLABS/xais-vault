"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useCreateApiKey } from "@/lib/hooks/use-api-keys";
import { createApiKeySchema, type CreateApiKeyFormData } from "@/lib/schemas/settings";
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

interface CreateApiKeyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (key: string) => void;
}

export function CreateApiKeyDialog({
  open,
  onOpenChange,
  onCreated,
}: CreateApiKeyDialogProps) {
  const t = useTranslations("settings");
  const createApiKey = useCreateApiKey();

  const { register, handleSubmit, reset, formState: { errors } } =
    useForm<CreateApiKeyFormData>({
      resolver: zodResolver(createApiKeySchema),
      defaultValues: { name: "", rpmLimit: 60, rpdLimit: 1000 },
    });

  async function onSubmit(data: CreateApiKeyFormData) {
    try {
      const result = await createApiKey.mutateAsync({
        name: data.name,
        scopes: ["*"],
        rpm_limit: data.rpmLimit,
        rpd_limit: data.rpdLimit,
      });
      if (result.data?.key) {
        reset();
        onCreated(result.data.key);
      }
    } catch {
      toast.error("Erreur lors de la création");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("apiKeys.create")}</DialogTitle>
          <DialogDescription>{t("apiKeys.description")}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="key-name">{t("apiKeys.nameLabel")}</Label>
            <Input
              id="key-name"
              placeholder={t("apiKeys.namePlaceholder")}
              {...register("name")}
            />
            {errors.name && (
              <p className="text-xs text-vault-danger">{errors.name.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="rpm-limit">{t("apiKeys.rpmLimitLabel")}</Label>
              <Input
                id="rpm-limit"
                type="number"
                min={1}
                {...register("rpmLimit", { valueAsNumber: true })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="rpd-limit">{t("apiKeys.rpdLimitLabel")}</Label>
              <Input
                id="rpd-limit"
                type="number"
                min={1}
                {...register("rpdLimit", { valueAsNumber: true })}
              />
            </div>
          </div>

          <div className="space-y-1">
            <Label>{t("apiKeys.scopesLabel")}</Label>
            <p className="text-sm text-vault-text-muted">{t("apiKeys.scopesAll")}</p>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={createApiKey.isPending}>
              {createApiKey.isPending
                ? t("apiKeys.creating")
                : t("apiKeys.createButton")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
