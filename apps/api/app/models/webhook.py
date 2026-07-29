"""
Webhook Pydantic models.
"""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator

# ─── Event types valides ──────────────────────────────────────────────────────

WEBHOOK_EVENTS = [
    "source.ready",
    "source.failed",
    "scan.completed",
    "insight.created",
    "investigation.completed",
    "deliverable.ready",
    "webhook.test",
]


class WebhookCreate(BaseModel):
    """Body pour créer un webhook."""

    url: HttpUrl
    events: list[str] = Field(..., min_length=1)
    is_active: bool = True

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str]) -> list[str]:
        invalid = [e for e in v if e not in WEBHOOK_EVENTS]
        if invalid:
            raise ValueError(
                f"Invalid event types: {invalid}. Valid types: {WEBHOOK_EVENTS}"
            )
        return v


class WebhookUpdate(BaseModel):
    """Body pour modifier un webhook."""

    url: HttpUrl | None = None
    events: list[str] | None = Field(default=None, min_length=1)
    is_active: bool | None = None

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        invalid = [e for e in v if e not in WEBHOOK_EVENTS]
        if invalid:
            raise ValueError(
                f"Invalid event types: {invalid}. Valid types: {WEBHOOK_EVENTS}"
            )
        return v


class WebhookResponse(BaseModel):
    """Réponse webhook — JAMAIS le secret."""

    id: str
    url: str
    events: list[str]
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


class WebhookCreated(WebhookResponse):
    """Réponse après création ou rotation — inclut le secret UNE SEULE FOIS."""

    secret: str  # whsec_{32_hex}


class WebhookDeliveryResponse(BaseModel):
    """Réponse pour une livraison de webhook."""

    id: str
    webhook_id: str
    event_type: str
    payload: dict
    status: str  # pending, delivered, failed
    attempt: int
    http_status: int | None = None
    response_body: str | None = None
    next_retry_at: datetime | None = None
    created_at: datetime
    delivered_at: datetime | None = None
