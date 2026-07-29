"""
Billing Pydantic models — checkout, portal, status.
"""

from pydantic import BaseModel, Field


class CheckoutRequest(BaseModel):
    price_id: str  # STRIPE_PRICE_STARTER ou STRIPE_PRICE_TEAM
    success_url: str = Field(..., pattern=r"^https?://")
    cancel_url: str = Field(..., pattern=r"^https?://")


class PortalRequest(BaseModel):
    return_url: str = Field(..., pattern=r"^https?://")


class BillingStatusResponse(BaseModel):
    plan: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    trial_ends_at: str | None
    limits: dict  # {max_workspaces, max_analyses_per_month}
    current_usage: dict  # {workspaces_count, analyses_this_month}
