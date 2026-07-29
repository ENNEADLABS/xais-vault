// Clé localStorage pour persister le plan choisi sur la landing
// pendant le flux signup/login → auto-checkout post-auth
export const PENDING_PLAN_KEY = "pending_checkout_plan";

// Clé localStorage pour persister l'intervalle (monthly/yearly)
export const PENDING_INTERVAL_KEY = "pending_checkout_interval";

export type BillingInterval = "monthly" | "yearly";

// Mapping plan landing → env var Stripe price_id (mensuel)
export const PLAN_PRICE_ENV: Record<string, string | undefined> = {
  starter: process.env.NEXT_PUBLIC_STRIPE_PRICE_STARTER,
  premium: process.env.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM,
  team: process.env.NEXT_PUBLIC_STRIPE_PRICE_TEAM,
};

// Mapping plan landing → env var Stripe price_id (annuel)
export const PLAN_PRICE_YEARLY_ENV: Record<string, string | undefined> = {
  starter: process.env.NEXT_PUBLIC_STRIPE_PRICE_STARTER_YEARLY,
  premium: process.env.NEXT_PUBLIC_STRIPE_PRICE_PREMIUM_YEARLY,
  team: process.env.NEXT_PUBLIC_STRIPE_PRICE_TEAM_YEARLY,
};
