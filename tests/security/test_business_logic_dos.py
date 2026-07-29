"""
Tests de sécurité — Logique métier & DoS (Phase 4)

Couvre :
- Job queue : injection, type validation, poisoning defense
- Billing : Stripe webhook HMAC requis et rejeté si invalide
- Limites plan : check_workspace_limit lève 403
- Chat : session hijacking inter-org bloqué
- SSE : message d'erreur générique (pas de str(e))
- DoS : limite sources par workspace (flooding), taille texte (Pydantic)
- Webhook : retry max respecté
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# ─── 1. Job Queue ────────────────────────────────────────────────────────────


class TestJobQueue:
    """La queue de jobs ne doit pas permettre l'injection ni le poisoning."""

    def test_create_job_rejects_unknown_type(self):
        """create_job doit lever ValueError si le type n'est pas dans JOB_TYPES."""
        from packages.db.job_queue import create_job

        db_mock = MagicMock()

        with pytest.raises(ValueError, match="Unknown job type"):
            import asyncio

            asyncio.run(
                create_job(
                    db_mock,
                    type="delete_all_data",  # Type arbitraire non autorisé
                    payload={},
                    organization_id="org-a",
                )
            )

    def test_job_types_whitelist_is_complete(self):
        """JOB_TYPES doit contenir exactement les types attendus."""
        from packages.db.job_queue import JOB_TYPES

        expected = {
            "index_source",
            "scan_workspace",
            "verify_insight",
            "investigate",
            "generate_deliverable",
            "dispatch_webhook",
        }
        assert set(JOB_TYPES) == expected

    @pytest.mark.asyncio
    async def test_indexing_rejects_cross_org_job(self):
        """Le worker doit détecter un job poisoning (source d'une autre org)."""
        from apps.worker.app.services.indexing import index_source

        supabase_mock = MagicMock()
        # Simuler un source appartenant à org-B
        supabase_mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": "src-1",
                    "workspace_id": "workspace-1",
                    "organization_id": "org-b",  # Appartient à org-B
                    "type": "txt",
                    "file_path": None,
                    "extracted_text": "test content",
                    "metadata": {},
                }
            ]
        )

        # Payload prétend que le job est de org-A
        payload = {
            "source_id": "src-1",
            "workspace_id": "workspace-1",
            "organization_id": "org-a",  # Org différente !
        }

        with pytest.raises(ValueError, match="Job poisoning detected"):
            await index_source(supabase_mock, payload)

    @pytest.mark.asyncio
    async def test_indexing_accepts_matching_org(self):
        """Le worker accepte le job si les org_id correspondent."""
        from apps.worker.app.services.indexing import index_source

        supabase_mock = MagicMock()
        supabase_mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        supabase_mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": "src-1",
                    "workspace_id": "workspace-1",
                    "organization_id": "org-a",
                    "type": "txt",
                    "file_path": None,
                    "extracted_text": "test content",
                    "metadata": {},
                }
            ]
        )

        payload = {
            "source_id": "src-1",
            "workspace_id": "workspace-1",
            "organization_id": "org-a",  # Correspond bien
            "skip_extraction": True,
        }

        # On patch les dépendances LLM/embed pour ne pas les appeler
        with (
            patch(
                "apps.worker.app.services.indexing.embed_chunks",
                new_callable=AsyncMock,
                return_value=([], 0.0),
            ),
            patch(
                "apps.worker.app.services.indexing.generate_summary",
                new_callable=AsyncMock,
                return_value=(
                    {"summary": "", "topics": [], "suggested_questions": []},
                    0.0,
                ),
            ),
            patch(
                "apps.worker.app.services.indexing.chunk_document",
                return_value=[{"content": "chunk", "tokens": 100}],
            ),
            patch(
                "apps.worker.app.services.indexing.store_chunks",
                new_callable=AsyncMock,
            ),
            patch(
                "apps.worker.app.services.indexing.maybe_trigger_scan",
                new_callable=AsyncMock,
            ),
            patch(
                "apps.worker.app.services.indexing._emit_webhook",
                new_callable=AsyncMock,
            ),
        ):
            result = await index_source(supabase_mock, payload)
        assert result["source_id"] == "src-1"


# ─── 2. Billing — Stripe Webhook Spoofing ────────────────────────────────────


class TestStripeWebhookSecurity:
    """Le webhook Stripe doit refuser les requêtes sans signature valide."""

    def test_stripe_webhook_rejects_missing_signature(self):
        """Sans header stripe-signature → 400."""
        from fastapi.testclient import TestClient

        from apps.api.app.main import app

        client = TestClient(app, raise_server_exceptions=False)

        with patch(
            "apps.api.app.routers.billing.load_config",
            return_value=MagicMock(stripe_webhook_secret="whsec_test"),
        ):
            response = client.post(
                "/api/v2/billing/webhooks/stripe",
                content=b'{"type":"checkout.session.completed"}',
                headers={"Content-Type": "application/json"},
                # Pas de stripe-signature
            )
        assert response.status_code == 400

    def test_stripe_webhook_rejects_invalid_signature(self):
        """Header stripe-signature invalide → 400."""
        import stripe
        from fastapi.testclient import TestClient

        from apps.api.app.main import app

        client = TestClient(app, raise_server_exceptions=False)

        with (
            patch(
                "apps.api.app.routers.billing.load_config",
                return_value=MagicMock(stripe_webhook_secret="whsec_real"),
            ),
            patch.object(
                stripe.Webhook,
                "construct_event",
                side_effect=stripe.error.SignatureVerificationError(
                    "invalid", "bad-sig"
                ),
            ),
        ):
            response = client.post(
                "/api/v2/billing/webhooks/stripe",
                content=b'{"type":"fake"}',
                headers={
                    "Content-Type": "application/json",
                    "stripe-signature": "t=fake,v1=forged",
                },
            )
        assert response.status_code == 400
        body = response.json()
        detail = body.get("detail") or body.get("error", {}).get("message", "")
        assert "signature" in detail.lower()

    def test_stripe_webhook_unconfigured_returns_503(self):
        """Sans STRIPE_WEBHOOK_SECRET configuré → 503."""
        from fastapi.testclient import TestClient

        from apps.api.app.main import app

        client = TestClient(app, raise_server_exceptions=False)

        with patch(
            "apps.api.app.routers.billing.load_config",
            return_value=MagicMock(stripe_webhook_secret=None),
        ):
            response = client.post(
                "/api/v2/billing/webhooks/stripe",
                content=b'{"type":"fake"}',
                headers={"Content-Type": "application/json"},
            )
        assert response.status_code == 503


# ─── 3. Limites Plan ─────────────────────────────────────────────────────────


class TestPlanLimits:
    """check_workspace_limit doit lever 403 quand la limite est atteinte."""

    @pytest.mark.asyncio
    async def test_deal_limit_raises_403_when_at_limit(self):
        """Un org au max de ses workspaces ne peut pas en créer un de plus."""
        from apps.api.app.services.plan_limits import check_workspace_limit

        db_mock = MagicMock()
        # Org sur plan starter avec 5 workspaces (limite)
        db_mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "org-1", "plan": "starter", "trial_ends_at": None}]
        )
        db_mock.table.return_value.select.return_value.eq.return_value.neq.return_value.execute.return_value = MagicMock(
            count=5  # Exactement à la limite
        )

        with pytest.raises(HTTPException) as exc_info:
            await check_workspace_limit(db_mock, "org-1")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_deal_limit_passes_when_below_limit(self):
        """Un org en dessous de sa limite peut créer un workspace."""
        from apps.api.app.services.plan_limits import check_workspace_limit

        db_mock = MagicMock()
        db_mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "org-1", "plan": "starter", "trial_ends_at": None}]
        )
        db_mock.table.return_value.select.return_value.eq.return_value.neq.return_value.execute.return_value = MagicMock(
            count=3  # En dessous de la limite de 5
        )

        # Ne doit pas lever d'exception
        await check_workspace_limit(db_mock, "org-1")

    @pytest.mark.asyncio
    async def test_enterprise_plan_has_no_limit(self):
        """Le plan enterprise est illimité."""
        from apps.api.app.services.plan_limits import check_workspace_limit

        db_mock = MagicMock()
        db_mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "org-1", "plan": "enterprise", "trial_ends_at": None}]
        )

        # Ne doit pas lever même avec 999 workspaces
        await check_workspace_limit(db_mock, "org-1")


# ─── 4. Chat — Session Hijacking ─────────────────────────────────────────────


class TestChatSessionSecurity:
    """Un user ne doit pas pouvoir accéder aux sessions d'une autre org."""

    @pytest.mark.asyncio
    async def test_cross_org_session_access_raises_404(self):
        """get_or_create_session doit lever 404 si la session n'appartient pas à l'org."""
        from apps.api.app.services.chat_session import get_or_create_session

        db_mock = MagicMock()
        # La session existe mais avec un organization_id différent
        db_mock.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]  # Pas trouvé avec le filtre org_id
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_or_create_session(
                db_mock,
                session_id="session-from-org-b",
                workspace_id="workspace-1",
                organization_id="org-a",  # L'org du user
                user_id="user-1",
                first_message="test",
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_valid_session_access_succeeds(self):
        """get_or_create_session réussit si la session appartient bien à l'org."""
        from apps.api.app.services.chat_session import get_or_create_session

        db_mock = MagicMock()
        db_mock.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "session-1"}]  # Session trouvée avec le bon org_id
        )

        result = await get_or_create_session(
            db_mock,
            session_id="session-1",
            workspace_id="workspace-1",
            organization_id="org-a",
            user_id="user-1",
            first_message="test",
        )
        assert result == "session-1"


# ─── 5. SSE — Info Leak ───────────────────────────────────────────────────────


class TestSSEErrorMessage:
    """Le stream SSE ne doit pas exposer les détails d'exception."""

    @pytest.mark.asyncio
    async def test_sse_error_message_is_generic(self):
        """En cas d'erreur, le message SSE est générique (pas de str(e))."""
        from apps.api.app.services.sse import build_chat_event_stream

        context_mock = MagicMock()
        context_mock.source_map = {}
        context_mock.rag_metadata = None

        # stream_response lève une exception interne avec des détails
        with patch(
            "apps.api.app.services.sse.stream_response",
            side_effect=Exception("DB connection refused to 10.0.0.1:5432"),
        ):
            events = []
            async for event in build_chat_event_stream(
                context=context_mock,
                session_id="session-1",
                organization_id="org-1",
                user_content="test",
                db=MagicMock(),
            ):
                events.append(event)

        # Récupérer l'événement error
        error_events = [e for e in events if "event: error" in e]
        assert len(error_events) == 1
        payload = json.loads(error_events[0].split("data: ")[1])
        # Le message doit être générique, pas les détails DB
        assert "10.0.0.1" not in payload["message"]
        assert "connection refused" not in payload["message"].lower()
        assert payload["message"] == "Exception at stream"


# ─── 6. DoS — Source Flooding ─────────────────────────────────────────────────


class TestSourceFlooding:
    """Limite de sources par workspace — protection contre le flooding."""

    @pytest.mark.asyncio
    async def test_upload_raises_429_when_limit_reached(self):
        """upload_file_source doit lever 429 si le workspace a trop de sources."""
        from apps.api.app.services.source_upload import upload_file_source
        from apps.api.app.services.source_validators import MAX_SOURCES_PER_WORKSPACE

        db_mock = MagicMock()
        # Workspace existe
        db_mock.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "workspace-1"}]
        )
        # Sources count = MAX
        db_mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=MAX_SOURCES_PER_WORKSPACE
        )

        file_mock = MagicMock()
        file_mock.filename = "test.pdf"

        with pytest.raises(HTTPException) as exc_info:
            await upload_file_source(
                workspace_id="workspace-1",
                organization_id="org-1",
                user_id="user-1",
                file=file_mock,
                db=db_mock,
            )
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_text_source_raises_429_when_limit_reached(self):
        """add_text_source doit lever 429 si le workspace a trop de sources."""
        from apps.api.app.services.source_upload import add_text_source
        from apps.api.app.services.source_validators import MAX_SOURCES_PER_WORKSPACE

        db_mock = MagicMock()
        db_mock.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "workspace-1"}]
        )
        db_mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=MAX_SOURCES_PER_WORKSPACE
        )

        with pytest.raises(HTTPException) as exc_info:
            await add_text_source(
                workspace_id="workspace-1",
                organization_id="org-1",
                user_id="user-1",
                name="test",
                content="some content",
                db=db_mock,
            )
        assert exc_info.value.status_code == 429

    def test_text_source_max_length_enforced_by_pydantic(self):
        """SourceTextCreate rejette le contenu > MAX_TEXT_SIZE."""
        from pydantic import ValidationError

        from apps.api.app.models.source import MAX_TEXT_SIZE, SourceTextCreate

        oversized_content = "x" * (MAX_TEXT_SIZE + 1)

        with pytest.raises(ValidationError):
            SourceTextCreate(name="test", content=oversized_content)


# ─── 7. Webhook Retry Limit ───────────────────────────────────────────────────


class TestWebhookRetryLimit:
    """MAX_RETRY_ATTEMPTS est respecté — pas de retry infini."""

    @pytest.mark.asyncio
    async def test_no_retry_at_max_attempts(self):
        """_schedule_retry ne crée pas de job si attempt >= MAX_RETRY_ATTEMPTS."""
        from apps.worker.app.services.webhook_dispatcher import (
            MAX_RETRY_ATTEMPTS,
            _schedule_retry,
        )

        db_mock = MagicMock()

        with patch(
            "apps.worker.app.services.webhook_dispatcher.create_job",
            new_callable=AsyncMock,
        ) as mock_create_job:
            await _schedule_retry(
                db_mock,
                webhook_id="wh-1",
                event_type="source.ready",
                payload={},
                organization_id="org-1",
                attempt=MAX_RETRY_ATTEMPTS,  # Exactement à la limite
            )

        # Aucun job de retry ne doit être créé
        mock_create_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_scheduled_below_max_attempts(self):
        """_schedule_retry crée bien un job si attempt < MAX_RETRY_ATTEMPTS."""
        from apps.worker.app.services.webhook_dispatcher import (
            _schedule_retry,
        )

        db_mock = MagicMock()
        db_mock.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "job-retry-1"}]
        )
        db_mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch(
            "apps.worker.app.services.webhook_dispatcher.create_job",
            new_callable=AsyncMock,
            return_value={"id": "job-retry-1"},
        ) as mock_create_job:
            await _schedule_retry(
                db_mock,
                webhook_id="wh-1",
                event_type="source.ready",
                payload={},
                organization_id="org-1",
                attempt=1,  # En dessous de la limite
            )

        mock_create_job.assert_called_once()
