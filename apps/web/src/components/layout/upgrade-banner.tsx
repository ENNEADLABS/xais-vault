"use client";

import { X, Zap } from "lucide-react";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useBillingStatus, useCreateCheckout } from "@/lib/hooks/use-billing";
import { Button } from "@/components/ui/button";

/**
 * Affiché quand l'utilisation dépasse 80% d'une limite ou que le trial expire dans < 3 jours.
 * À placer dans le layout principal.
 */
export function UpgradeBanner() {
  const t = useTranslations("common");
  const [dismissed, setDismissed] = useState(false);
  const [now] = useState(() => Date.now());
  const { data } = useBillingStatus();
  const checkout = useCreateCheckout();

  if (dismissed || !data?.data) return null;

  const { plan, limits, current_usage, trial_ends_at } = data.data;

  // Ne pas afficher pour Enterprise
  if (plan === "enterprise") return null;

  // Calcul seuils
  const workspacesNearLimit =
    limits.max_workspaces !== null &&
    current_usage.workspaces_count / limits.max_workspaces >= 0.8;
  const analysesNearLimit =
    limits.max_analyses_per_month !== null &&
    current_usage.analyses_this_month / limits.max_analyses_per_month >= 0.8;

  const trialExpiringSoon =
    plan === "trial" &&
    trial_ends_at !== null &&
    isTrialExpiringSoon(trial_ends_at, now);

  const shouldShow = workspacesNearLimit || analysesNearLimit || trialExpiringSoon;
  if (!shouldShow) return null;

  const message = trialExpiringSoon
    ? t("bannerTrialExpiring")
    : workspacesNearLimit
      ? t("bannerWorkspacesLimit")
      : t("bannerAnalysesLimit");

  const currentUrl = typeof window !== "undefined" ? window.location.href : "";

  // Propose le plan supérieur au plan actuel
  function getNextPriceId(): string {
    if (plan === "trial" || plan === "starter") return process.env.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM ?? "";
    if (plan === "premium") return process.env.NEXT_PUBLIC_STRIPE_PRICE_TEAM ?? "";
    return process.env.NEXT_PUBLIC_STRIPE_PRICE_TEAM ?? "";
  }

  function handleUpgrade() {
    checkout.mutate({
      price_id: getNextPriceId(),
      success_url: `${currentUrl}?billing=success`,
      cancel_url: currentUrl,
    });
  }

  return (
    <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-2 flex items-center justify-between gap-4 text-sm">
      <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
        <Zap className="h-4 w-4 shrink-0" />
        <span>{message}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs border-amber-500/40"
          onClick={handleUpgrade}
          disabled={checkout.isPending}
        >
          {t("upgrade")}
        </Button>
        <button
          onClick={() => setDismissed(true)}
          className="text-muted-foreground hover:text-foreground transition-colors"
          aria-label={t("close")}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

export function isTrialExpiringSoon(trialEndsAt: string, now: number): boolean {
  const daysLeft = Math.ceil(
    (new Date(trialEndsAt).getTime() - now) / (1000 * 60 * 60 * 24),
  );
  return daysLeft >= 0 && daysLeft <= 3;
}
