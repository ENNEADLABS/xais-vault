"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useRouter, Link } from "@/i18n/navigation";
import { useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { createDefaultOrganization } from "@/lib/auth/create-default-org";
import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/form-error";
import { TerminalField } from "@/components/ui/terminal-field";
import { ConfirmationSentCard } from "./confirmation-sent-card";
import { cn } from "@/lib/utils";
import { signupSchema, type SignupFormData } from "@/lib/schemas/auth";
import { PENDING_PLAN_KEY, PENDING_INTERVAL_KEY } from "@/lib/constants/billing";

export function SignupForm() {
  const t = useTranslations("auth.signup");
  const router = useRouter();
  const supabase = createClient();
  const searchParams = useSearchParams();

  // Persiste le plan et l'intervalle choisis sur la landing pour post-signup checkout
  useEffect(() => {
    const plan = searchParams.get("plan");
    const interval = searchParams.get("interval");
    if (plan) localStorage.setItem(PENDING_PLAN_KEY, plan);
    if (interval) localStorage.setItem(PENDING_INTERVAL_KEY, interval);
  }, [searchParams]);

  const [serverError, setServerError] = useState<string | null>(null);
  const [confirmationSent, setConfirmationSent] = useState(false);

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
    defaultValues: { fullName: "", email: "", password: "", confirmPassword: "" },
  });

  async function onSubmit(data: SignupFormData) {
    setServerError(null);

    const { data: authData, error: authError } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
      options: { data: { full_name: data.fullName } },
    });

    if (authError) {
      setServerError(authError.message);
      return;
    }

    if (authData.user && !authData.session) {
      setConfirmationSent(true);
      return;
    }

    if (authData.session) {
      const displayName = data.fullName || data.email;
      const orgName = t("defaultOrgName", { name: displayName });
      await createDefaultOrganization(displayName, orgName);
      router.push("/workspaces");
      router.refresh();
    }
  }

  if (confirmationSent) return <ConfirmationSentCard email={getValues("email")} />;

  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-vault-text">{t("title")}</h2>
        <p className="text-sm text-vault-text-secondary">{t("description")}</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <TerminalField
          id="fullName"
          label={t("fullNameLabel")}
          type="text"
          placeholder={t("fullNamePlaceholder")}
          error={errors.fullName?.message}
          {...register("fullName")}
        />

        <TerminalField
          id="email"
          label={t("emailLabel")}
          type="email"
          placeholder={t("emailPlaceholder")}
          error={errors.email?.message}
          {...register("email")}
        />

        <TerminalField
          id="password"
          label={t("passwordLabel")}
          type="password"
          error={errors.password?.message}
          {...register("password")}
        />

        <TerminalField
          id="confirmPassword"
          label={t("confirmPasswordLabel")}
          type="password"
          error={errors.confirmPassword?.message ? t("passwordMismatch") : undefined}
          {...register("confirmPassword")}
        />

        <FormError message={serverError} />

        <Button
          type="submit"
          disabled={isSubmitting}
          className={cn(
            "h-12 w-full rounded-none bg-vault-accent font-mono text-sm font-semibold",
            "tracking-[0.15em] text-vault-bg uppercase",
            "hover:bg-vault-accent-hover transition-colors",
            "disabled:opacity-50",
          )}
        >
          {isSubmitting ? t("submitLoading") : t("submit")}
        </Button>
      </form>

      <p className="text-sm text-vault-text-secondary">
        {t("hasAccount")}{" "}
        <Link
          href={searchParams.get("plan")
            ? `/login?plan=${searchParams.get("plan")}${searchParams.get("interval") ? `&interval=${searchParams.get("interval")}` : ""}`
            : "/login"}
          className="text-vault-accent hover:text-vault-accent-hover transition-colors"
        >
          {t("loginLink")}
        </Link>
      </p>
    </div>
  );
}
