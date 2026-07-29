"use client";

import { useEffect, useRef } from "react";
import { useCreateCheckout } from "@/lib/hooks/use-billing";
import {
  PENDING_PLAN_KEY,
  PENDING_INTERVAL_KEY,
  PLAN_PRICE_ENV,
  PLAN_PRICE_YEARLY_ENV,
} from "@/lib/constants/billing";

/**
 * Composant invisible monté dans le layout app.
 * Détecte un plan pending en localStorage (posé par la landing → signup/login)
 * et déclenche automatiquement le checkout Stripe avec le bon price_id
 * selon l'intervalle choisi (monthly par défaut).
 */
export function PendingCheckoutTrigger() {
  const checkout = useCreateCheckout();
  const triggered = useRef(false);

  useEffect(() => {
    if (triggered.current) return;

    const plan = localStorage.getItem(PENDING_PLAN_KEY);
    if (!plan) return;

    const interval = localStorage.getItem(PENDING_INTERVAL_KEY) ?? "monthly";
    const priceMap = interval === "yearly" ? PLAN_PRICE_YEARLY_ENV : PLAN_PRICE_ENV;
    const priceId = priceMap[plan];

    if (!priceId) {
      localStorage.removeItem(PENDING_PLAN_KEY);
      localStorage.removeItem(PENDING_INTERVAL_KEY);
      return;
    }

    triggered.current = true;
    localStorage.removeItem(PENDING_PLAN_KEY);
    localStorage.removeItem(PENDING_INTERVAL_KEY);

    checkout.mutate({
      price_id: priceId,
      success_url: `${window.location.origin}/workspaces?billing=success`,
      cancel_url: `${window.location.origin}/workspaces`,
    });
  }, [checkout]);

  return null;
}
