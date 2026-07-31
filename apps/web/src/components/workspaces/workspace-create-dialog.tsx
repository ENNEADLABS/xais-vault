"use client";

import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { useCreateWorkspace } from "@/lib/hooks/use-workspaces";
import { workspaceCreateSchema, type WorkspaceCreateFormData } from "@/lib/schemas/workspaces";
import { FormError } from "@/components/ui/form-error";
import { Textarea } from "@/components/ui/textarea";
import { TerminalField } from "@/components/ui/terminal-field";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmojiPicker } from "./emoji-picker";
import { WorkspaceFormFields } from "./workspace-form-fields";
import { useState } from "react";

interface WorkspaceCreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function WorkspaceCreateDialog({ open, onOpenChange }: WorkspaceCreateDialogProps) {
  const t = useTranslations("workspaces.create");
  const router = useRouter();
  const { mutateAsync, isPending } = useCreateWorkspace();
  const [serverError, setServerError] = useState<string | null>(null);

  const { control, register, handleSubmit, setValue, formState: { errors } } =
    useForm<WorkspaceCreateFormData>({
      resolver: zodResolver(workspaceCreateSchema),
      defaultValues: {
        name: "",
        emoji: "briefcase",
        description: "",
        workspaceType: "",
        sector: "",
        targetCompany: "",
      },
    });

  const emoji = useWatch({ control, name: "emoji" });
  const workspaceType = useWatch({ control, name: "workspaceType" });
  const sector = useWatch({ control, name: "sector" });

  async function onSubmit(data: WorkspaceCreateFormData) {
    setServerError(null);
    try {
      const result = await mutateAsync({
        name: data.name,
        emoji: data.emoji,
        description: data.description || undefined,
        deal_type: data.workspaceType || undefined,
        sector: data.sector || undefined,
        target_company: data.targetCompany || undefined,
      });

      if (result.data?.id) {
        onOpenChange(false);
        router.push(`/workspaces/${result.data.id}`);
      }
    } catch {
      setServerError("Une erreur est survenue. Veuillez réessayer.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md bg-vault-surface">
        <DialogHeader>
          <DialogTitle className="font-mono text-[14px] uppercase tracking-wider font-semibold">
            {t("title")}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <EmojiPicker
            selected={emoji}
            onSelect={(v) => setValue("emoji", v)}
            label={t("emojiLabel")}
          />
          <TerminalField
            id="workspace-name"
            label={t("nameLabel")}
            placeholder={t("namePlaceholder")}
            error={errors.name?.message}
            {...register("name")}
          />
          <WorkspaceFormFields
            workspaceType={workspaceType ?? ""}
            onWorkspaceTypeChange={(v) => setValue("workspaceType", v)}
            sector={sector ?? ""}
            onSectorChange={(v) => setValue("sector", v)}
          />
          <TerminalField
            id="target-company"
            label={t("targetCompanyLabel")}
            placeholder={t("targetCompanyPlaceholder")}
            error={errors.targetCompany?.message}
            {...register("targetCompany")}
          />
          <div className="space-y-1.5">
            <p className="font-mono text-[12px] uppercase tracking-wider text-vault-text-secondary mb-1.5">
              {t("descriptionLabel")}
            </p>
            <Textarea
              id="description"
              placeholder={t("descriptionPlaceholder")}
              rows={3}
              className="bg-vault-surface border border-vault-border rounded-lg text-[13px] text-vault-text p-3 focus-visible:ring-0 focus-visible:border-vault-accent transition-colors duration-150 resize-none"
              {...register("description")}
            />
          </div>
          <FormError message={serverError} />
          <button
            type="submit"
            disabled={isPending}
            className="w-full bg-vault-accent text-black font-mono text-[13px] uppercase tracking-wide rounded-none py-2.5 hover:bg-vault-accent/90 disabled:opacity-50 transition-colors duration-150"
          >
            {isPending ? t("submitting") : t("submit")}
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
