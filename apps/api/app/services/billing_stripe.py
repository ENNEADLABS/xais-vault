"""
Stripe helpers — client, checkout, portal, customer management.
Extracted from billing.py.
"""

import logging

import stripe
from fastapi import HTTPException

from packages.core.config import load_config

logger = logging.getLogger(__name__)


def _get_stripe_client() -> stripe.StripeClient:
    """Retourne un client Stripe initialisé. Lève 503 si non configuré."""
    config = load_config()
    if not config.stripe_secret_key:
        raise HTTPException(
            status_code=503,
            detail="Billing not configured. Contact support.",
        )
    return stripe.StripeClient(config.stripe_secret_key)


def _price_to_plan(price_id: str) -> str:
    """Mappe un Stripe Price ID vers un nom de plan DB."""
    config = load_config()
    if price_id == config.stripe_price_starter:
        return "starter"
    if price_id == config.stripe_price_premium:
        return "premium"
    if price_id == config.stripe_price_team:
        return "team"
    return "starter"  # Fallback sécurisé


def _get_allowed_price_ids() -> list[str]:
    """Retourne la liste des price IDs autorisés pour le checkout."""
    config = load_config()
    return [
        p
        for p in [
            config.stripe_price_starter,
            config.stripe_price_premium,
            config.stripe_price_team,
        ]
        if p
    ]


async def _get_or_create_customer(
    db, organization_id: str, client: stripe.StripeClient
) -> str:
    """Retourne le stripe_customer_id existant ou en crée un nouveau."""
    result = (
        db.table("organizations")
        .select("id, name, stripe_customer_id")
        .eq("id", organization_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Organization not found")

    org = result.data[0]
    if org.get("stripe_customer_id"):
        return org["stripe_customer_id"]

    # Créer le customer Stripe
    customer = client.customers.create(
        params={
            "name": org["name"],
            "metadata": {"organization_id": organization_id},
        }
    )

    # Persister le customer_id
    db.table("organizations").update(
        {
            "stripe_customer_id": customer.id,
        }
    ).eq("id", organization_id).execute()

    return customer.id


async def create_checkout_session(
    db,
    organization_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Crée une Checkout Session Stripe. Retourne l'URL de redirection."""
    allowed = _get_allowed_price_ids()
    if price_id not in allowed:
        raise HTTPException(status_code=400, detail="Invalid price ID")

    client = _get_stripe_client()
    customer_id = await _get_or_create_customer(db, organization_id, client)

    session = client.checkout.sessions.create(
        params={
            "customer": customer_id,
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {"organization_id": organization_id},
            "subscription_data": {"metadata": {"organization_id": organization_id}},
        }
    )

    return session.url


async def create_portal_session(db, organization_id: str, return_url: str) -> str:
    """Crée une session Billing Portal Stripe. Retourne l'URL de redirection."""
    result = (
        db.table("organizations")
        .select("stripe_customer_id")
        .eq("id", organization_id)
        .execute()
    )
    if not result.data or not result.data[0].get("stripe_customer_id"):
        raise HTTPException(
            status_code=400,
            detail="No active subscription. Start a checkout first.",
        )

    client = _get_stripe_client()
    session = client.billing_portal.sessions.create(
        params={
            "customer": result.data[0]["stripe_customer_id"],
            "return_url": return_url,
        }
    )

    return session.url
