"""
Billing router — Stripe checkout, portal, status, webhooks.

Le endpoint /webhooks/stripe n'a PAS d'auth JWT — sécurisé par signature Stripe.
"""

import logging

import stripe
from fastapi import APIRouter, HTTPException, Request

from packages.core.config import load_config

from ..dependencies import DB, AdminAuth
from ..models.billing import BillingStatusResponse, CheckoutRequest, PortalRequest
from ..models.common import ApiResponse
from ..services import billing

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/checkout", status_code=200)
async def create_checkout(body: CheckoutRequest, auth: AdminAuth, db: DB):
    """Create a Stripe Checkout session for plan upgrade. Admin only."""
    url = await billing.create_checkout_session(
        db=db,
        organization_id=auth.organization_id,
        price_id=body.price_id,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
    )
    return ApiResponse(data={"url": url})


@router.post("/portal", status_code=200)
async def create_portal(body: PortalRequest, auth: AdminAuth, db: DB):
    """Create a Stripe Billing Portal session. Admin only."""
    url = await billing.create_portal_session(
        db=db,
        organization_id=auth.organization_id,
        return_url=body.return_url,
    )
    return ApiResponse(data={"url": url})


@router.get("/status")
async def get_billing_status(auth: AdminAuth, db: DB):
    """Get current billing status for the organization. Admin only."""
    status = await billing.get_billing_status(
        db=db, organization_id=auth.organization_id
    )
    return ApiResponse(data=BillingStatusResponse(**status))


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: DB):
    """Handle Stripe webhook events. No auth — verified by HMAC signature."""
    payload = (
        await request.body()
    )  # Raw bytes — critique pour la vérification de signature
    sig_header = request.headers.get("stripe-signature")
    config = load_config()

    if not config.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, config.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook: invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as exc:
        logger.error("Stripe webhook parse error: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        await billing.handle_checkout_completed(db, data_object)
    elif event_type == "customer.subscription.updated":
        await billing.sync_subscription(db, data_object)
    elif event_type == "customer.subscription.deleted":
        await billing.handle_subscription_deleted(db, data_object)
    elif event_type == "invoice.payment_failed":
        logger.warning(
            "Payment failed for customer %s",
            data_object.get("customer"),
        )
    else:
        logger.debug("Unhandled Stripe event: %s", event_type)

    return {"received": True}
