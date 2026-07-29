"use client";

import { CreditCard, Zap } from "lucide-react";
import { useBillingStatus, useCreateCheckout, useCreatePortal } from "@/lib/hooks/use-billing";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const PLAN_LABELS: Record<string, string> = {
  starter: "Starter",
  premium: "Premium",
  team: "Team",
  enterprise: "Enterprise",
  trial: "Essai gratuit",
};

const PLAN_BADGE_CLASSES: Record<string, string> = {
  starter: "bg-vault-border/40 text-vault-text-secondary",
  premium: "bg-vault-accent-dim text-vault-accent",
  team: "bg-vault-accent-dim text-vault-accent",
  enterprise: "bg-vault-accent-dim text-vault-accent",
  trial: "bg-vault-border/40 text-vault-text-muted",
};

function UsageBar({ current, max, label }: { current: number; max: number | null; label: string }) {
  if (max === null) {
    return (
      <div className="flex justify-between text-xs text-vault-text-muted">
        <span>{label}</span>
        <span>{current} / illimité</span>
      </div>
    );
  }

  const pct = Math.min(100, Math.round((current / max) * 100));
  const isWarning = pct >= 80;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-vault-text-muted">{label}</span>
        <span className={isWarning ? "text-vault-warning font-medium" : "text-vault-text-muted"}>
          {current} / {max}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-vault-border/30 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${isWarning ? "bg-vault-warning" : "bg-vault-accent"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function TrialCountdown({ trialEndsAt }: { trialEndsAt: string }) {
  const end = new Date(trialEndsAt);
  const now = new Date();
  const daysLeft = Math.max(0, Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)));

  if (daysLeft === 0) {
    return <p className="text-xs text-destructive">Essai expiré</p>;
  }

  return (
    <p className="text-xs text-vault-text-muted">
      {daysLeft} jour{daysLeft > 1 ? "s" : ""} restant{daysLeft > 1 ? "s" : ""} dans l&apos;essai
    </p>
  );
}

export function BillingSection() {
  const { data, isLoading } = useBillingStatus();
  const checkout = useCreateCheckout();
  const portal = useCreatePortal();

  const currentUrl = typeof window !== "undefined" ? window.location.href : "";

  function handleUpgrade(priceId: string) {
    checkout.mutate({
      price_id: priceId,
      success_url: `${currentUrl}?billing=success`,
      cancel_url: currentUrl,
    });
  }

  function handleManage() {
    portal.mutate(currentUrl);
  }

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-lg">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-10 w-32" />
      </div>
    );
  }

  const status = data?.data;
  if (!status) return null;

  const { plan, limits, current_usage, trial_ends_at, stripe_subscription_id } = status;

  return (
    <div className="space-y-6 max-w-lg">
      <div>
        <h3 className="text-sm font-medium">Plan actuel</h3>
        <p className="text-xs text-vault-text-muted mt-0.5">
          Gérez votre abonnement et vos limites d&apos;utilisation.
        </p>
      </div>

      {/* Plan badge + trial countdown */}
      <div className="flex items-center gap-3">
        <span className={cn("rounded px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide", PLAN_BADGE_CLASSES[plan] ?? "bg-vault-border/40 text-vault-text-secondary")}>
          {PLAN_LABELS[plan] ?? plan}
        </span>
        {plan === "trial" && trial_ends_at && (
          <TrialCountdown trialEndsAt={trial_ends_at} />
        )}
      </div>

      {/* Usage */}
      <div className="border border-vault-border rounded-lg p-4 space-y-3">
        <p className="text-xs font-medium text-vault-text-muted uppercase tracking-wider">
          Utilisation ce mois
        </p>
        <UsageBar
          current={current_usage.workspaces_count}
          max={limits.max_workspaces}
          label="Workspaces actifs"
        />
        <UsageBar
          current={current_usage.analyses_this_month}
          max={limits.max_analyses_per_month}
          label="Analyses"
        />
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        {stripe_subscription_id ? (
          <Button
            variant="outline"
            size="sm"
            onClick={handleManage}
            disabled={portal.isPending}
          >
            <CreditCard className="h-4 w-4 mr-2" />
            Gérer l&apos;abonnement
          </Button>
        ) : plan !== "enterprise" && (
          <>
            {plan !== "starter" && plan !== "premium" && plan !== "team" && (
              <Button
                size="sm"
                onClick={() => handleUpgrade(process.env.NEXT_PUBLIC_STRIPE_PRICE_STARTER ?? "")}
                disabled={checkout.isPending}
              >
                <Zap className="h-4 w-4 mr-2" />
                Passer à Starter — 199€/mois
              </Button>
            )}
            {plan !== "premium" && plan !== "team" && (
              <Button
                size="sm"
                variant="default"
                onClick={() => handleUpgrade(process.env.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM ?? "")}
                disabled={checkout.isPending}
              >
                <Zap className="h-4 w-4 mr-2" />
                Passer à Premium — 299€/mois
              </Button>
            )}
            {plan !== "team" && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleUpgrade(process.env.NEXT_PUBLIC_STRIPE_PRICE_TEAM ?? "")}
                disabled={checkout.isPending}
              >
                <Zap className="h-4 w-4 mr-2" />
                Passer à Team — 499€/mois
              </Button>
            )}
          </>
        )}
      </div>

      {plan === "enterprise" && (
        <p className="text-xs text-vault-text-muted">
          Plan Enterprise — contactez-nous pour toute modification.
        </p>
      )}
    </div>
  );
}
