"use client";

import { useTranslations } from "next-intl";
import { Check } from "lucide-react";

interface ConfirmationSentCardProps {
  email: string;
}

export function ConfirmationSentCard({ email }: ConfirmationSentCardProps) {
  const t = useTranslations("auth.signup");
  return (
    <div className="space-y-3 border border-vault-border bg-vault-surface p-8">
      <div className="flex items-center gap-2">
        <Check className="h-5 w-5 text-vault-success" />
        <p className="font-mono text-sm font-semibold text-vault-text">
          {t("checkEmail")}
        </p>
      </div>
      <p className="text-sm text-vault-text-secondary">
        {t("confirmationSent", { email })}
      </p>
    </div>
  );
}
