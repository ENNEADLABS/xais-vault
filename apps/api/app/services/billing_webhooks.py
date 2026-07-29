"""
Stripe webhook handlers — subscription sync, checkout, cancellation.
Extracted from billing.py.
"""

import logging

from .billing_stripe import _get_stripe_client, _price_to_plan

logger = logging.getLogger(__name__)


async def sync_subscription(db, subscription: dict) -> None:
    """Synchronise l'état Stripe → DB depuis un objet subscription."""
    organization_id = (subscription.get("metadata") or {}).get("organization_id")
    if not organization_id:
        logger.warning(
            "Stripe subscription %s has no organization_id in metadata",
            subscription.get("id"),
        )
        return

    # Extraire le plan depuis le premier item
    plan = "starter"
    items_data = (subscription.get("items") or {}).get("data") or []
    if items_data:
        price_id = (items_data[0].get("price") or {}).get("id")
        if price_id:
            plan = _price_to_plan(price_id)

    # Downgrade si subscription supprimée ou expirée
    status = subscription.get("status", "")
    if status in ("canceled", "unpaid", "incomplete_expired"):
        plan = "starter"

    updates: dict = {
        "plan": plan,
        "stripe_subscription_id": subscription.get("id"),
    }

    db.table("organizations").update(updates).eq("id", organization_id).execute()
    logger.info(
        "Synced org %s → plan=%s (subscription=%s)",
        organization_id,
        plan,
        subscription.get("id"),
    )


async def handle_checkout_completed(db, session: dict) -> None:
    """Callback post-checkout réussi — lie le customer et active le plan."""
    organization_id = (session.get("metadata") or {}).get("organization_id")
    if not organization_id:
        logger.warning("checkout.session.completed: no organization_id in metadata")
        return

    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if customer_id:
        db.table("organizations").update(
            {
                "stripe_customer_id": customer_id,
            }
        ).eq("id", organization_id).execute()

    if subscription_id:
        # Récupérer la subscription pour avoir le price_id
        client = _get_stripe_client()
        subscription = client.subscriptions.retrieve(subscription_id)
        await sync_subscription(
            db,
            subscription.to_dict()
            if hasattr(subscription, "to_dict")
            else dict(subscription),
        )


async def handle_subscription_deleted(db, subscription: dict) -> None:
    """Callback suppression d'abonnement — downgrade vers starter."""
    organization_id = (subscription.get("metadata") or {}).get("organization_id")
    if not organization_id:
        return

    db.table("organizations").update(
        {
            "plan": "starter",
            "stripe_subscription_id": None,
        }
    ).eq("id", organization_id).execute()
    logger.info(
        "Subscription deleted for org %s — downgraded to starter", organization_id
    )
