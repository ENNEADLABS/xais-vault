-- Ajoute 'premium' à la CHECK constraint `organizations.plan`.
--
-- Bug runtime potentiel : le code (apps/api/app/services/plan_limits.py:15,
-- apps/api/app/services/billing_stripe.py:33,46) écrit la valeur 'premium'
-- en DB lors d'un checkout Stripe Premium, mais la contrainte initiale
-- (supabase/schema.sql:20) ne l'autorise pas → 23514 check_violation au
-- premier upgrade Premium.
--
-- Découvert lors de l'audit de cohérence docs ↔ code (2026-05-12).

alter table public.organizations
  drop constraint if exists organizations_plan_check;

alter table public.organizations
  add constraint organizations_plan_check
  check (plan in ('starter', 'premium', 'team', 'enterprise', 'trial'));
