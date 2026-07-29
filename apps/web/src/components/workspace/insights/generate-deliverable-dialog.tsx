"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useCreateDeliverable } from "@/lib/hooks/use-deliverables";
import {
  generateDeliverableSchema,
  type GenerateDeliverableFormData,
} from "@/lib/schemas/workspaces";
import type { Deliverable } from "@/types/api";

interface GenerateDeliverableDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  dealName: string;
}

// Labels par défaut — wording généraliste (pivot Phase 1).
// Les clés techniques (executive_summary / investment_memo / dd_report)
// restent inchangées côté backend / DB pour préserver l'historique.
const TYPE_DEFAULT_NAMES: Record<Deliverable["type"], string> = {
  executive_summary: "Synthèse",
  investment_memo: "Mémo d'analyse",
  dd_report: "Rapport complet",
};

export function GenerateDeliverableDialog({
  open,
  onOpenChange,
  workspaceId,
  dealName,
}: GenerateDeliverableDialogProps) {
  const t = useTranslations("deliverables");
  const { mutate: create, isPending } = useCreateDeliverable(workspaceId);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<GenerateDeliverableFormData>({
    resolver: zodResolver(generateDeliverableSchema),
    defaultValues: {
      type: "executive_summary",
      name: `${TYPE_DEFAULT_NAMES["executive_summary"]} — ${dealName}`,
    },
  });

  const type = watch("type");

  useEffect(() => {
    setValue("name", `${TYPE_DEFAULT_NAMES[type]} — ${dealName}`);
  }, [type, dealName, setValue]);

  function onSubmit(data: GenerateDeliverableFormData) {
    create(
      { type: data.type, name: data.name },
      {
        onSuccess: () => {
          toast.success(t("generationLaunched"));
          onOpenChange(false);
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{t("dialogTitle")}</DialogTitle>
          <DialogDescription>{t("dialogDescription")}</DialogDescription>
        </DialogHeader>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-3 pt-1"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              {t("typeLabel")}
            </label>
            <Select
              value={type}
              onValueChange={(v) => {
                if (v)
                  setValue("type", v as GenerateDeliverableFormData["type"]);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="executive_summary">
                  {t("typeExecutiveSummary")}
                </SelectItem>
                <SelectItem value="investment_memo">
                  {t("typeInvestmentMemo")}
                </SelectItem>
                <SelectItem value="dd_report">{t("typeDdReport")}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              {t("nameLabel")}
            </label>
            <Input placeholder={t("namePlaceholder")} {...register("name")} />
            {errors.name && (
              <p className="text-xs text-vault-danger">{errors.name.message}</p>
            )}
          </div>

          <Button type="submit" disabled={isPending}>
            {isPending ? t("generating") : t("generateButton")}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
