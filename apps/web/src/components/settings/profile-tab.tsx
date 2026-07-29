"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useProfile, useUpdateProfile } from "@/lib/hooks/use-profile";
import { profileSchema, type ProfileFormData } from "@/lib/schemas/settings";
import { TerminalField } from "@/components/ui/terminal-field";
import { Skeleton } from "@/components/ui/skeleton";

export function ProfileTab() {
  const t = useTranslations("settings");
  const { data, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();
  const profile = data?.data;

  const { register, handleSubmit, reset, formState: { errors } } =
    useForm<ProfileFormData>({
      resolver: zodResolver(profileSchema),
      defaultValues: { displayName: "", avatarUrl: "" },
    });

  useEffect(() => {
    if (profile) {
      reset({
        displayName: profile.display_name ?? "",
        avatarUrl: profile.avatar_url ?? "",
      });
    }
  }, [profile, reset]);

  async function onSubmit(data: ProfileFormData) {
    try {
      await updateProfile.mutateAsync({
        display_name: data.displayName || undefined,
        avatar_url: data.avatarUrl || undefined,
      });
      toast.success(t("profile.saved"));
    } catch {
      toast.error("Erreur lors de la mise à jour");
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <p className="font-semibold text-[16px] text-vault-text mb-1">{t("tabs.profile")}</p>
          <p className="text-[13px] text-vault-text-muted">{t("profile.description")}</p>
        </div>
        <div className="space-y-5">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="font-semibold text-[16px] text-vault-text mb-1">{t("tabs.profile")}</p>
        <p className="text-[13px] text-vault-text-muted">{t("profile.description")}</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <TerminalField
          id="display-name"
          label={t("profile.displayName")}
          placeholder={t("profile.displayNamePlaceholder")}
          error={errors.displayName?.message}
          {...register("displayName")}
        />

        <div className="space-y-1.5">
          <p className="font-mono text-[12px] uppercase tracking-wider text-vault-text-secondary">
            {t("profile.email")}
          </p>
          <input
            value={profile?.email ?? ""}
            disabled
            className="w-full bg-transparent border-b border-vault-border text-[13px] text-vault-text-muted py-2 outline-none cursor-not-allowed"
          />
          <p className="text-[11px] text-vault-text-muted">{t("profile.emailReadOnly")}</p>
        </div>

        <TerminalField
          id="avatar-url"
          label={t("profile.avatarUrl")}
          placeholder={t("profile.avatarUrlPlaceholder")}
          error={errors.avatarUrl?.message}
          {...register("avatarUrl")}
        />

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={updateProfile.isPending}
            className="bg-vault-accent text-black font-mono text-[13px] uppercase tracking-wide rounded-none px-6 py-2.5 hover:bg-vault-accent/90 disabled:opacity-50 transition-colors duration-150"
          >
            {updateProfile.isPending ? t("profile.saving") : t("profile.save")}
          </button>
        </div>
      </form>
    </div>
  );
}
