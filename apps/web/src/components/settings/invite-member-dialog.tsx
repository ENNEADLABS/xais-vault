"use client";

import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useInviteMember } from "@/lib/hooks/use-organization";
import { inviteMemberSchema, type InviteMemberFormData } from "@/lib/schemas/settings";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface InviteMemberDialogProps {
  orgId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function InviteMemberDialog({
  orgId,
  open,
  onOpenChange,
}: InviteMemberDialogProps) {
  const t = useTranslations("settings");
  const inviteMember = useInviteMember(orgId);

  const { control, register, handleSubmit, setValue, reset, formState: { errors } } =
    useForm<InviteMemberFormData>({
      resolver: zodResolver(inviteMemberSchema),
      defaultValues: { email: "", role: "analyst" },
    });

  const role = useWatch({ control, name: "role" });

  async function onSubmit(data: InviteMemberFormData) {
    try {
      await inviteMember.mutateAsync({ email: data.email, role: data.role });
      toast.success(t("invite.success"));
      reset();
      onOpenChange(false);
    } catch (err: unknown) {
      const code = (err as { error?: { code?: number } })?.error?.code;
      if (code === 409) {
        toast.error(t("invite.alreadyMember"));
      } else {
        toast.error("Erreur lors de l'invitation");
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("invite.title")}</DialogTitle>
          <DialogDescription>{t("invite.description")}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="invite-email">{t("invite.emailLabel")}</Label>
            <Input
              id="invite-email"
              type="email"
              placeholder={t("invite.emailPlaceholder")}
              {...register("email")}
            />
            {errors.email && (
              <p className="text-xs text-vault-danger">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="invite-role">{t("invite.roleLabel")}</Label>
            <Select
              value={role}
              onValueChange={(v) => {
                if (v) setValue("role", v as InviteMemberFormData["role"]);
              }}
            >
              <SelectTrigger id="invite-role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">{t("organization.roleAdmin")}</SelectItem>
                <SelectItem value="analyst">{t("organization.roleAnalyst")}</SelectItem>
                <SelectItem value="viewer">{t("organization.roleViewer")}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={inviteMember.isPending}>
              {inviteMember.isPending ? t("invite.submitting") : t("invite.submit")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
