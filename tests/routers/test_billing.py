"""
Tests for apps/api/app/routers/billing.py

Auth et DB mockés via dependency override.
Stripe webhook testé avec signature valide et invalide.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.app.dependencies import get_db, require_admin
from apps.api.app.main import app
from apps.api.app.services.auth import AuthContext

# ─── Constants ─────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
CHECKOUT_URL = "https://checkout.stripe.com/pay/cs_test_abc"
PORTAL_URL = "https://billing.stripe.com/p/session/test_xyz"


# ─── Helpers ───────────────────────────────────────────────────


def _make_admin_auth() -> AuthContext:
    return AuthContext(
        user_id=USER_ID,
        organization_id=ORG_ID,
        role="admin",
        auth_method="jwt",
    )


def _make_config(
    stripe_webhook_secret: str = "whsec_test",
    stripe_price_starter: str = "price_starter_123",
    stripe_price_premium: str = "price_premium_789",
    stripe_price_team: str = "price_team_456",
):
    cfg = MagicMock()
    cfg.stripe_secret_key = "sk_test_abc"
    cfg.stripe_webhook_secret = stripe_webhook_secret
    cfg.stripe_price_starter = stripe_price_starter
    cfg.stripe_price_premium = stripe_price_premium
    cfg.stripe_price_team = stripe_price_team
    return cfg


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _make_admin_auth()
    yield
    app.dependency_overrides.clear()


# ─── POST /billing/checkout ─────────────────────────────────────


@pytest.mark.asyncio
async def test_create_checkout_returns_url(client, mock_db):
    with patch(
        "apps.api.app.routers.billing.billing.create_checkout_session",
        new=AsyncMock(return_value=CHECKOUT_URL),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/v2/billing/checkout",
                json={
                    "price_id": "price_starter_123",
                    "success_url": "https://app.example.com/billing/success",
                    "cancel_url": "https://app.example.com/billing/cancel",
                },
                headers={"X-Organization-ID": ORG_ID},
            )

    assert resp.status_code == 200
    assert resp.json()["data"]["url"] == CHECKOUT_URL


@pytest.mark.asyncio
async def test_create_checkout_invalid_url_returns_422(client, mock_db):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/api/v2/billing/checkout",
            json={
                "price_id": "price_starter_123",
                "success_url": "not-a-url",  # URL invalide
                "cancel_url": "https://app.example.com/cancel",
            },
            headers={"X-Organization-ID": ORG_ID},
        )

    assert resp.status_code == 422


# ─── POST /billing/portal ────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_portal_returns_url(client, mock_db):
    with patch(
        "apps.api.app.routers.billing.billing.create_portal_session",
        new=AsyncMock(return_value=PORTAL_URL),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/v2/billing/portal",
                json={"return_url": "https://app.example.com/settings"},
                headers={"X-Organization-ID": ORG_ID},
            )

    assert resp.status_code == 200
    assert resp.json()["data"]["url"] == PORTAL_URL


# ─── GET /billing/status ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_billing_status_returns_data(client, mock_db):
    status_data = {
        "plan": "trial",
        "stripe_customer_id": None,
        "stripe_subscription_id": None,
        "trial_ends_at": "2026-03-31T00:00:00+00:00",
        "limits": {"max_workspaces": 20, "max_analyses_per_month": 200},
        "current_usage": {"workspaces_count": 2, "analyses_this_month": 5},
    }
    with patch(
        "apps.api.app.routers.billing.billing.get_billing_status",
        new=AsyncMock(return_value=status_data),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v2/billing/status",
                headers={"X-Organization-ID": ORG_ID},
            )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["plan"] == "trial"
    assert data["limits"]["max_workspaces"] == 20


# ─── POST /billing/webhooks/stripe ───────────────────────────────


@pytest.mark.asyncio
async def test_stripe_webhook_invalid_signature_returns_400():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    cfg = _make_config()
    with patch("apps.api.app.routers.billing.load_config", return_value=cfg):
        with patch(
            "apps.api.app.routers.billing.stripe.Webhook.construct_event",
            side_effect=Exception("Invalid signature"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v2/billing/webhooks/stripe",
                    content=b'{"type": "checkout.session.completed"}',
                    headers={"stripe-signature": "t=invalid,v1=bad"},
                )

    app.dependency_overrides.clear()
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_stripe_webhook_checkout_completed_dispatches():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test", "metadata": {"organization_id": ORG_ID}}},
    }

    cfg = _make_config()
    with patch("apps.api.app.routers.billing.load_config", return_value=cfg):
        with patch(
            "apps.api.app.routers.billing.stripe.Webhook.construct_event",
            return_value=event,
        ):
            with patch(
                "apps.api.app.routers.billing.billing.handle_checkout_completed",
                new=AsyncMock(),
            ) as mock_handler:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    resp = await ac.post(
                        "/api/v2/billing/webhooks/stripe",
                        content=json.dumps(event).encode(),
                        headers={"stripe-signature": "t=123,v1=abc"},
                    )

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json() == {"received": True}
    mock_handler.assert_called_once()


@pytest.mark.asyncio
async def test_stripe_webhook_subscription_updated_dispatches():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_test",
                "status": "active",
                "metadata": {"organization_id": ORG_ID},
            }
        },
    }

    cfg = _make_config()
    with patch("apps.api.app.routers.billing.load_config", return_value=cfg):
        with patch(
            "apps.api.app.routers.billing.stripe.Webhook.construct_event",
            return_value=event,
        ):
            with patch(
                "apps.api.app.routers.billing.billing.sync_subscription",
                new=AsyncMock(),
            ) as mock_sync:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as ac:
                    resp = await ac.post(
                        "/api/v2/billing/webhooks/stripe",
                        content=json.dumps(event).encode(),
                        headers={"stripe-signature": "t=123,v1=abc"},
                    )

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    mock_sync.assert_called_once()


@pytest.mark.asyncio
async def test_stripe_webhook_no_secret_returns_503():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    cfg = _make_config(stripe_webhook_secret="")
    cfg.stripe_webhook_secret = None
    with patch("apps.api.app.routers.billing.load_config", return_value=cfg):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/v2/billing/webhooks/stripe",
                content=b"{}",
                headers={"stripe-signature": "t=123,v1=abc"},
            )

    app.dependency_overrides.clear()
    assert resp.status_code == 503
