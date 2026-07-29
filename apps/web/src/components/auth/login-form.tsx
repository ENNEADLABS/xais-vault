"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/form-error";
import { TerminalField } from "@/components/ui/terminal-field";
import { useLoginForm } from "@/lib/hooks/use-login-form";
import { cn } from "@/lib/utils";
import { PENDING_PLAN_KEY, PENDING_INTERVAL_KEY } from "@/lib/constants/billing";

export function LoginForm() {
  const t = useTranslations("auth.login");
  const searchParams = useSearchParams();

  // Persiste le plan et l'intervalle choisis sur la landing pour post-login checkout
  useEffect(() => {
    const plan = searchParams.get("plan");
    const interval = searchParams.get("interval");
    if (plan) localStorage.setItem(PENDING_PLAN_KEY, plan);
    if (interval) localStorage.setItem(PENDING_INTERVAL_KEY, interval);
  }, [searchParams]);

  const {
    mode,
    setMode,
    passwordForm,
    magicLinkForm,
    loading,
    error,
    magicLinkSent,
    handlePasswordLogin,
    handleMagicLink,
  } = useLoginForm();

  if (magicLinkSent) {
    return (
      <div className="space-y-3 border border-vault-border bg-vault-bg/50 p-8">
        <p className="font-mono text-xs tracking-[0.2em] text-vault-accent uppercase">
          {t("checkEmail")}
        </p>
        <p className="text-sm text-vault-text-secondary">
          {t("magicLinkSent", { email: magicLinkForm.getValues("email") })}
        </p>
      </div>
    );
  }

  const isPassword = mode === "password";
  const form = isPassword ? passwordForm : magicLinkForm;

  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold text-vault-text">{t("title")}</h2>
        <p className="text-sm text-vault-text-secondary">
          {isPassword ? t("descriptionPassword") : t("descriptionMagicLink")}
        </p>
      </div>

      <form
        onSubmit={
          isPassword
            ? passwordForm.handleSubmit(handlePasswordLogin)
            : magicLinkForm.handleSubmit(handleMagicLink)
        }
        className="space-y-6"
      >
        <TerminalField
          id="email"
          label={t("emailLabel")}
          type="email"
          placeholder={t("emailPlaceholder")}
          error={form.formState.errors.email?.message}
          {...(isPassword
            ? passwordForm.register("email")
            : magicLinkForm.register("email"))}
        />

        {isPassword && (
          <TerminalField
            id="password"
            label={t("passwordLabel")}
            type="password"
            error={passwordForm.formState.errors.password?.message}
            {...passwordForm.register("password")}
          />
        )}

        <FormError message={error} />

        <Button
          type="submit"
          disabled={loading}
          className={cn(
            "h-12 w-full rounded-none bg-vault-accent font-mono text-sm font-semibold",
            "tracking-[0.15em] text-vault-bg uppercase",
            "hover:bg-vault-accent-hover transition-colors",
            "disabled:opacity-50",
          )}
        >
          {loading
            ? t("submitLoading")
            : isPassword
              ? t("submitPassword")
              : t("submitMagicLink")}
        </Button>
      </form>

      <div className="space-y-4">
        <button
          type="button"
          onClick={() => setMode(isPassword ? "magic-link" : "password")}
          className="text-xs text-vault-text-secondary hover:text-vault-text transition-colors underline underline-offset-4"
        >
          {isPassword ? t("switchToMagicLink") : t("switchToPassword")}
        </button>

        <p className="text-sm text-vault-text-secondary">
          {t("noAccount")}{" "}
          <Link
            href={searchParams.get("plan")
              ? `/signup?plan=${searchParams.get("plan")}${searchParams.get("interval") ? `&interval=${searchParams.get("interval")}` : ""}`
              : "/signup"}
            className="text-vault-accent hover:text-vault-accent-hover transition-colors"
          >
            {t("signupLink")}
          </Link>
        </p>
      </div>
    </div>
  );
}
