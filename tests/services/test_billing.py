"""
Tests for the Stripe billing service (apps/api/app/services/billing.py).

Stripe SDK est mocké — aucun appel réseau réel.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

ORG_ID = str(uuid.uuid4())
CUSTOMER_ID = "cus_test_123"
SUBSCRIPTION_ID = "sub_test_456"
CHECKOUT_URL = "https://checkout.stripe.com/pay/cs_test_123"
PORTAL_URL = "https://billing.stripe.com/p/session/test_456"


def _make_config(
    stripe_secret_key: str = "sk_test_abc",
    stripe_price_starter: str = "price_starter_123",
    stripe_price_premium: str = "price_premium_789",
    stripe_price_team: str = "price_team_456",
    stripe_webhook_secret: str = "whsec_test",
):
    """Config mock avec Stripe configuré."""
    cfg = MagicMock()
    cfg.stripe_secret_key = stripe_secret_key
    cfg.stripe_price_starter = stripe_price_starter
    cfg.stripe_price_premium = stripe_price_premium
    cfg.stripe_price_team = stripe_price_team
    cfg.stripe_webhook_secret = stripe_webhook_secret
    return cfg


def _make_db_org(
    plan: str = "starter",
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    trial_ends_at: str | None = None,
):
    """Mock Supabase retournant une organisation."""
    db = MagicMock()
    org_data = {
        "id": ORG_ID,
        "name": "Acme PE",
        "plan": plan,
        "stripe_customer_id": stripe_customer_id,
        "stripe_subscription_id": stripe_subscription_id,
        "trial_ends_at": trial_ends_at,
    }
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[org_data])
    )
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[org_data])
    )
    db.table.return_value.select.return_value.eq.return_value.neq.return_value.execute.return_value = MagicMock(
        data=[], count=2
    )
    db.table.return_value.select.return_value.eq.return_value.in_.return_value.gte.return_value.execute.return_value = MagicMock(
        data=[], count=5
    )
    return db


# ─── _price_to_plan ──────────────────────────────────────────────


def test_price_to_plan_starter():
    from apps.api.app.services.billing_stripe import _price_to_plan

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        assert _price_to_plan("price_starter_123") == "starter"


def test_price_to_plan_premium():
    from apps.api.app.services.billing_stripe import _price_to_plan

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        assert _price_to_plan("price_premium_789") == "premium"


def test_price_to_plan_team():
    from apps.api.app.services.billing_stripe import _price_to_plan

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        assert _price_to_plan("price_team_456") == "team"


def test_price_to_plan_unknown_falls_back_to_starter():
    from apps.api.app.services.billing_stripe import _price_to_plan

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        assert _price_to_plan("price_unknown_999") == "starter"


# ─── create_checkout_session ──────────────────────────────────────


@pytest.mark.asyncio
async def test_create_checkout_session_invalid_price_raises_400():
    from apps.api.app.services.billing import create_checkout_session

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        db = _make_db_org()
        with pytest.raises(HTTPException) as exc:
            await create_checkout_session(
                db, ORG_ID, "price_invalid", "https://ok.com", "https://cancel.com"
            )
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_checkout_session_no_stripe_key_raises_503():
    from apps.api.app.services.billing import create_checkout_session

    cfg = _make_config(stripe_secret_key="")
    cfg.stripe_secret_key = None
    with patch("apps.api.app.services.billing_stripe.load_config", return_value=cfg):
        db = _make_db_org()
        with pytest.raises(HTTPException) as exc:
            await create_checkout_session(
                db, ORG_ID, "price_starter_123", "https://ok.com", "https://cancel.com"
            )
        assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_create_checkout_session_returns_url():
    from apps.api.app.services.billing import create_checkout_session

    mock_session = MagicMock()
    mock_session.url = CHECKOUT_URL

    mock_customer = MagicMock()
    mock_customer.id = CUSTOMER_ID

    mock_client = MagicMock()
    mock_client.customers.create.return_value = mock_customer
    mock_client.checkout.sessions.create.return_value = mock_session

    db = _make_db_org()

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        with patch(
            "apps.api.app.services.billing_stripe.stripe.StripeClient",
            return_value=mock_client,
        ):
            url = await create_checkout_session(
                db, ORG_ID, "price_starter_123", "https://ok.com", "https://cancel.com"
            )

    assert url == CHECKOUT_URL


# ─── create_portal_session ────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_portal_session_no_customer_raises_400():
    from apps.api.app.services.billing import create_portal_session

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        db = _make_db_org(stripe_customer_id=None)
        with pytest.raises(HTTPException) as exc:
            await create_portal_session(db, ORG_ID, "https://return.com")
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_portal_session_returns_url():
    from apps.api.app.services.billing import create_portal_session

    mock_session = MagicMock()
    mock_session.url = PORTAL_URL

    mock_client = MagicMock()
    mock_client.billing_portal.sessions.create.return_value = mock_session

    db = _make_db_org(stripe_customer_id=CUSTOMER_ID)

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        with patch(
            "apps.api.app.services.billing_stripe.stripe.StripeClient",
            return_value=mock_client,
        ):
            url = await create_portal_session(db, ORG_ID, "https://return.com")

    assert url == PORTAL_URL


# ─── sync_subscription ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_subscription_updates_plan_to_team():
    from apps.api.app.services.billing import sync_subscription

    db = _make_db_org()
    subscription = {
        "id": SUBSCRIPTION_ID,
        "status": "active",
        "metadata": {"organization_id": ORG_ID},
        "items": {"data": [{"price": {"id": "price_team_456"}}]},
    }

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        await sync_subscription(db, subscription)

    db.table.return_value.update.assert_called_once()
    update_args = db.table.return_value.update.call_args[0][0]
    assert update_args["plan"] == "team"


@pytest.mark.asyncio
async def test_sync_subscription_canceled_downgrades_to_starter():
    from apps.api.app.services.billing import sync_subscription

    db = _make_db_org(plan="team")
    subscription = {
        "id": SUBSCRIPTION_ID,
        "status": "canceled",
        "metadata": {"organization_id": ORG_ID},
        "items": {"data": [{"price": {"id": "price_team_456"}}]},
    }

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        await sync_subscription(db, subscription)

    update_args = db.table.return_value.update.call_args[0][0]
    assert update_args["plan"] == "starter"


@pytest.mark.asyncio
async def test_sync_subscription_no_org_id_skipped():
    from apps.api.app.services.billing import sync_subscription

    db = MagicMock()
    subscription = {
        "id": SUBSCRIPTION_ID,
        "status": "active",
        "metadata": {},  # Pas d'organization_id
        "items": {"data": []},
    }

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        await sync_subscription(db, subscription)

    db.table.assert_not_called()


# ─── handle_subscription_deleted ─────────────────────────────────


@pytest.mark.asyncio
async def test_handle_subscription_deleted_downgrades():
    from apps.api.app.services.billing import handle_subscription_deleted

    db = _make_db_org(plan="team")
    subscription = {
        "id": SUBSCRIPTION_ID,
        "metadata": {"organization_id": ORG_ID},
    }

    await handle_subscription_deleted(db, subscription)

    update_args = db.table.return_value.update.call_args[0][0]
    assert update_args["plan"] == "starter"
    assert update_args["stripe_subscription_id"] is None


@pytest.mark.asyncio
async def test_handle_subscription_deleted_no_org_id_is_noop():
    from apps.api.app.services.billing import handle_subscription_deleted

    db = MagicMock()
    subscription = {"id": SUBSCRIPTION_ID, "metadata": {}}  # Pas d'organization_id

    await handle_subscription_deleted(db, subscription)

    db.table.assert_not_called()


# ─── _get_or_create_customer ──────────────────────────────────────


@pytest.mark.asyncio
async def test_checkout_session_org_not_found_raises_404():
    from apps.api.app.services.billing import create_checkout_session

    db = MagicMock()
    # DB retourne data vide → org introuvable
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[])
    )

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        with patch("apps.api.app.services.billing_stripe.stripe.StripeClient"):
            with pytest.raises(HTTPException) as exc:
                await create_checkout_session(
                    db,
                    ORG_ID,
                    "price_starter_123",
                    "https://ok.com",
                    "https://cancel.com",
                )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_checkout_session_uses_existing_customer_id():
    from apps.api.app.services.billing import create_checkout_session

    mock_session = MagicMock()
    mock_session.url = CHECKOUT_URL
    mock_client = MagicMock()
    mock_client.checkout.sessions.create.return_value = mock_session

    # Org avec customer_id déjà existant — pas de création Stripe
    db = _make_db_org(stripe_customer_id=CUSTOMER_ID)

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        with patch(
            "apps.api.app.services.billing_stripe.stripe.StripeClient",
            return_value=mock_client,
        ):
            url = await create_checkout_session(
                db, ORG_ID, "price_starter_123", "https://ok.com", "https://cancel.com"
            )

    # Aucune création de customer
    mock_client.customers.create.assert_not_called()
    assert url == CHECKOUT_URL


# ─── handle_checkout_completed ───────────────────────────────────


@pytest.mark.asyncio
async def test_handle_checkout_completed_no_org_id_is_noop():
    from apps.api.app.services.billing import handle_checkout_completed

    db = MagicMock()
    session = {"metadata": {}, "customer": CUSTOMER_ID, "subscription": None}

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        await handle_checkout_completed(db, session)

    db.table.assert_not_called()


@pytest.mark.asyncio
async def test_handle_checkout_completed_persists_customer_id():
    from apps.api.app.services.billing import handle_checkout_completed

    db = _make_db_org()
    session = {
        "metadata": {"organization_id": ORG_ID},
        "customer": CUSTOMER_ID,
        "subscription": None,  # Pas de subscription → sync_subscription non appelé
    }

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        await handle_checkout_completed(db, session)

    # Vérifie que stripe_customer_id est sauvegardé
    update_args = db.table.return_value.update.call_args[0][0]
    assert update_args["stripe_customer_id"] == CUSTOMER_ID


@pytest.mark.asyncio
async def test_handle_checkout_completed_syncs_subscription():
    from apps.api.app.services.billing import handle_checkout_completed

    db = _make_db_org()
    mock_sub = MagicMock()
    mock_sub.to_dict.return_value = {
        "id": SUBSCRIPTION_ID,
        "status": "active",
        "metadata": {"organization_id": ORG_ID},
        "items": {"data": [{"price": {"id": "price_premium_789"}}]},
    }
    mock_client = MagicMock()
    mock_client.subscriptions.retrieve.return_value = mock_sub

    session = {
        "metadata": {"organization_id": ORG_ID},
        "customer": CUSTOMER_ID,
        "subscription": SUBSCRIPTION_ID,
    }

    with patch(
        "apps.api.app.services.billing_stripe.load_config", return_value=_make_config()
    ):
        with patch(
            "apps.api.app.services.billing_stripe.stripe.StripeClient",
            return_value=mock_client,
        ):
            await handle_checkout_completed(db, session)

    mock_client.subscriptions.retrieve.assert_called_once_with(SUBSCRIPTION_ID)


# ─── get_billing_status ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_billing_status_org_not_found_raises_404():
    from apps.api.app.services.billing import get_billing_status

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[])
    )

    with pytest.raises(HTTPException) as exc:
        await get_billing_status(db, ORG_ID)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_billing_status_returns_plan_and_usage():
    from apps.api.app.services.billing import get_billing_status

    db = _make_db_org(plan="premium", stripe_customer_id=CUSTOMER_ID)

    result = await get_billing_status(db, ORG_ID)

    assert result["plan"] == "premium"
    assert "limits" in result
    assert "current_usage" in result
    assert "workspaces_count" in result["current_usage"]
    assert "analyses_this_month" in result["current_usage"]


@pytest.mark.asyncio
async def test_get_billing_status_includes_stripe_ids():
    from apps.api.app.services.billing import get_billing_status

    db = _make_db_org(
        stripe_customer_id=CUSTOMER_ID, stripe_subscription_id=SUBSCRIPTION_ID
    )

    result = await get_billing_status(db, ORG_ID)

    assert result["stripe_customer_id"] == CUSTOMER_ID
    assert result["stripe_subscription_id"] == SUBSCRIPTION_ID
