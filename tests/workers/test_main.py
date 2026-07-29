"""
Tests unitaires pour apps/worker/app/main.py.

Toutes les dépendances externes (Supabase, handlers) sont mockées.
Les imports dynamiques dans process_job sont injectés via sys.modules.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── Fixtures ────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_worker_imports():
    """Injecte des modules mockés pour les imports dynamiques de process_job.

    Sans ça, Python tente d'importer app.services.indexing, etc.,
    qui n'existe pas en dehors du contexte du worker.
    """
    fake_modules: dict[str, MagicMock] = {}
    modules_to_mock = [
        "app.services.indexing",
        "app.agents.scanner",
        "app.agents.verifier",
        "app.agents.researcher",
        "app.agents.writer",
        "app.services.webhook_dispatcher",
    ]
    for mod_name in modules_to_mock:
        mock = MagicMock()
        fake_modules[mod_name] = mock
        sys.modules[mod_name] = mock

    yield fake_modules

    for mod_name in modules_to_mock:
        sys.modules.pop(mod_name, None)


@pytest.fixture
def mock_supabase():
    return MagicMock()


# ─── handle_signal ────────────────────────────────────────────────


def test_handle_signal_sets_shutdown():
    import apps.worker.app.main as worker_main

    worker_main.SHUTDOWN = False
    worker_main.handle_signal(15, None)
    assert worker_main.SHUTDOWN is True
    worker_main.SHUTDOWN = False  # reset


def test_handle_signal_idempotent():
    import apps.worker.app.main as worker_main

    worker_main.SHUTDOWN = False
    worker_main.handle_signal(2, None)
    worker_main.handle_signal(2, None)
    assert worker_main.SHUTDOWN is True
    worker_main.SHUTDOWN = False  # reset


# ─── process_job ─────────────────────────────────────────────────


class TestProcessJob:
    @pytest.mark.asyncio
    async def test_index_source(self, mock_supabase, mock_worker_imports):
        from apps.worker.app.main import process_job

        mock_worker_imports["app.services.indexing"].index_source = AsyncMock(
            return_value={"indexed": 3}
        )
        job = {"id": "j1", "type": "index_source", "payload": {"source_id": "s1"}}

        result = await process_job(mock_supabase, job)

        assert result == {"indexed": 3}
        mock_worker_imports[
            "app.services.indexing"
        ].index_source.assert_called_once_with(mock_supabase, {"source_id": "s1"})

    @pytest.mark.asyncio
    async def test_scan_deal(self, mock_supabase, mock_worker_imports):
        from apps.worker.app.main import process_job

        mock_worker_imports["app.agents.scanner"].run_scan = AsyncMock(
            return_value={"insights": 5}
        )
        job = {"id": "j2", "type": "scan_workspace", "payload": {"workspace_id": "d1"}}

        result = await process_job(mock_supabase, job)

        assert result == {"insights": 5}

    @pytest.mark.asyncio
    async def test_verify_finding(self, mock_supabase, mock_worker_imports):
        from apps.worker.app.main import process_job

        mock_worker_imports["app.agents.verifier"].run_verification = AsyncMock(
            return_value={"verified": True}
        )
        job = {"id": "j3", "type": "verify_insight", "payload": {"insight_id": "f1"}}

        result = await process_job(mock_supabase, job)

        assert result == {"verified": True}

    @pytest.mark.asyncio
    async def test_investigate(self, mock_supabase, mock_worker_imports):
        from apps.worker.app.main import process_job

        mock_worker_imports["app.agents.researcher"].run_investigation = AsyncMock(
            return_value={"report": "done"}
        )
        job = {"id": "j4", "type": "investigate", "payload": {"workspace_id": "d1"}}

        result = await process_job(mock_supabase, job)

        assert result == {"report": "done"}

    @pytest.mark.asyncio
    async def test_generate_deliverable(self, mock_supabase, mock_worker_imports):
        from apps.worker.app.main import process_job

        mock_worker_imports["app.agents.writer"].run_generation = AsyncMock(
            return_value={"docx_url": "https://..."}
        )
        job = {"id": "j5", "type": "generate_deliverable", "payload": {"workspace_id": "d1"}}

        result = await process_job(mock_supabase, job)

        assert result == {"docx_url": "https://..."}

    @pytest.mark.asyncio
    async def test_dispatch_webhook(self, mock_supabase, mock_worker_imports):
        from apps.worker.app.main import process_job

        mock_worker_imports[
            "app.services.webhook_dispatcher"
        ].deliver_webhook = AsyncMock(return_value={"delivered": True})
        job = {
            "id": "j6",
            "type": "dispatch_webhook",
            "payload": {"webhook_id": "w1", "event": "workspace.scanned"},
        }

        result = await process_job(mock_supabase, job)

        assert result == {"delivered": True}

    @pytest.mark.asyncio
    async def test_unknown_type_raises_value_error(self, mock_supabase):
        from apps.worker.app.main import process_job

        job = {"id": "j7", "type": "explode_server", "payload": {}}

        with pytest.raises(ValueError, match="Unknown job type"):
            await process_job(mock_supabase, job)

    @pytest.mark.asyncio
    async def test_missing_payload_defaults_to_empty_dict(
        self, mock_supabase, mock_worker_imports
    ):
        from apps.worker.app.main import process_job

        mock_worker_imports["app.services.indexing"].index_source = AsyncMock(
            return_value={"ok": True}
        )
        # Pas de "payload" dans le job
        job = {"id": "j8", "type": "index_source"}

        result = await process_job(mock_supabase, job)

        mock_worker_imports[
            "app.services.indexing"
        ].index_source.assert_called_once_with(mock_supabase, {})


# ─── run_loop ────────────────────────────────────────────────────


class TestRunLoop:
    @pytest.mark.asyncio
    async def test_complete_job_called_on_success(
        self, mock_supabase, mock_worker_imports
    ):
        """Job trouvé + handler OK → complete_job appelé."""
        import apps.worker.app.main as worker_main

        job = {
            "id": "j1",
            "type": "index_source",
            "payload": {},
            "attempts": 0,
            "max_attempts": 3,
        }
        mock_worker_imports["app.services.indexing"].index_source = AsyncMock(
            return_value={"ok": True}
        )

        # claim_next_job retourne le job une fois, puis None pour stopper la boucle
        claim_side_effects = [job, None]

        async def mock_run_loop():
            """Version simplifiée de run_loop sans create_task."""
            for _ in range(2):
                claimed = claim_side_effects.pop(0) if claim_side_effects else None
                if claimed:
                    try:
                        result = await worker_main.process_job(mock_supabase, claimed)
                        await complete_job_mock(
                            mock_supabase, claimed["id"], result=result
                        )
                    except Exception as e:
                        await fail_job_mock(
                            mock_supabase,
                            claimed["id"],
                            error_message=str(e),
                            attempts=1,
                        )

        complete_job_mock = AsyncMock()
        fail_job_mock = AsyncMock()

        with patch.object(worker_main, "complete_job", complete_job_mock):
            with patch.object(worker_main, "fail_job", fail_job_mock):
                await mock_run_loop()

        complete_job_mock.assert_called_once_with(
            mock_supabase, "j1", result={"ok": True}
        )
        fail_job_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_fail_job_called_on_handler_error(
        self, mock_supabase, mock_worker_imports
    ):
        """Handler lève une exception → fail_job appelé."""
        import apps.worker.app.main as worker_main

        job = {
            "id": "j2",
            "type": "scan_workspace",
            "payload": {},
            "attempts": 1,
            "max_attempts": 3,
        }
        mock_worker_imports["app.agents.scanner"].run_scan = AsyncMock(
            side_effect=RuntimeError("Scan failed")
        )

        complete_job_mock = AsyncMock()
        fail_job_mock = AsyncMock()

        async def mock_run_loop():
            try:
                result = await worker_main.process_job(mock_supabase, job)
                await complete_job_mock(mock_supabase, job["id"], result=result)
            except Exception as e:
                await fail_job_mock(
                    mock_supabase,
                    job["id"],
                    error_message=str(e),
                    attempts=job.get("attempts", 1),
                    max_attempts=job.get("max_attempts", 3),
                )

        with patch.object(worker_main, "complete_job", complete_job_mock):
            with patch.object(worker_main, "fail_job", fail_job_mock):
                await mock_run_loop()

        fail_job_mock.assert_called_once()
        call_kwargs = fail_job_mock.call_args.kwargs
        assert "Scan failed" in call_kwargs["error_message"]
        complete_job_mock.assert_not_called()


# ─── recovery_loop ───────────────────────────────────────────────


class TestRecoveryLoop:
    @pytest.mark.asyncio
    async def test_logs_when_jobs_recovered(self, mock_supabase):
        from apps.worker.app.worker_loops import recovery_loop

        stopped = [False]

        def should_stop():
            return stopped[0]

        async def mock_sleep(secs):
            stopped[0] = True  # Stoppe après le premier sleep

        with patch(
            "apps.worker.app.worker_loops.recover_stuck_jobs", new_callable=AsyncMock
        ) as mock_recover:
            mock_recover.return_value = 2
            with patch("asyncio.sleep", side_effect=mock_sleep):
                await recovery_loop(mock_supabase, should_stop)

        mock_recover.assert_called_once_with(mock_supabase)

    @pytest.mark.asyncio
    async def test_exception_in_recover_does_not_crash_loop(self, mock_supabase):
        from apps.worker.app.worker_loops import recovery_loop

        stopped = [False]

        def should_stop():
            return stopped[0]

        async def mock_sleep(secs):
            stopped[0] = True

        with patch(
            "apps.worker.app.worker_loops.recover_stuck_jobs", new_callable=AsyncMock
        ) as mock_recover:
            mock_recover.side_effect = RuntimeError("DB down")
            with patch("asyncio.sleep", side_effect=mock_sleep):
                await recovery_loop(mock_supabase, should_stop)  # Ne doit pas lever


# ─── gc_loop ─────────────────────────────────────────────────────


class TestGcLoop:
    @pytest.mark.asyncio
    async def test_calls_all_cleanup_functions(self, mock_supabase):
        from apps.worker.app.worker_loops import gc_loop

        stopped = [False]

        def should_stop():
            return stopped[0]

        async def mock_sleep(secs):
            stopped[0] = True

        with (
            patch(
                "apps.worker.app.worker_loops.cleanup_old_jobs", new_callable=AsyncMock
            ) as mock_jobs,
            patch(
                "apps.worker.app.worker_loops.cleanup_old_traces",
                new_callable=AsyncMock,
            ) as mock_traces,
            patch(
                "apps.worker.app.worker_loops.cleanup_old_webhook_deliveries",
                new_callable=AsyncMock,
            ) as mock_webhooks,
        ):
            mock_jobs.return_value = {"completed_deleted": 0, "failed_deleted": 0}
            mock_traces.return_value = 0
            mock_webhooks.return_value = 0
            with patch("asyncio.sleep", side_effect=mock_sleep):
                await gc_loop(mock_supabase, should_stop)

        mock_jobs.assert_called_once_with(mock_supabase)
        mock_traces.assert_called_once_with(mock_supabase)
        mock_webhooks.assert_called_once_with(mock_supabase)

    @pytest.mark.asyncio
    async def test_exception_does_not_crash_gc_loop(self, mock_supabase):
        from apps.worker.app.worker_loops import gc_loop

        stopped = [False]

        def should_stop():
            return stopped[0]

        async def mock_sleep(secs):
            stopped[0] = True

        with patch(
            "apps.worker.app.worker_loops.cleanup_old_jobs", new_callable=AsyncMock
        ) as mock_jobs:
            mock_jobs.side_effect = RuntimeError("GC error")
            with patch("asyncio.sleep", side_effect=mock_sleep):
                await gc_loop(mock_supabase, should_stop)  # Ne doit pas lever

    @pytest.mark.asyncio
    async def test_logs_when_items_deleted(self, mock_supabase):
        """Vérifie que logger.info est appelé quand total > 0."""
        from apps.worker.app.worker_loops import gc_loop

        stopped = [False]

        def should_stop():
            return stopped[0]

        async def mock_sleep(secs):
            stopped[0] = True

        with (
            patch(
                "apps.worker.app.worker_loops.cleanup_old_jobs", new_callable=AsyncMock
            ) as mock_jobs,
            patch(
                "apps.worker.app.worker_loops.cleanup_old_traces",
                new_callable=AsyncMock,
            ) as mock_traces,
            patch(
                "apps.worker.app.worker_loops.cleanup_old_webhook_deliveries",
                new_callable=AsyncMock,
            ) as mock_webhooks,
            patch("apps.worker.app.worker_loops.logger") as mock_logger,
        ):
            mock_jobs.return_value = {"completed_deleted": 3, "failed_deleted": 1}
            mock_traces.return_value = 2
            mock_webhooks.return_value = 0
            with patch("asyncio.sleep", side_effect=mock_sleep):
                await gc_loop(mock_supabase, should_stop)

        mock_logger.info.assert_called()


# ─── supervised_recovery_loop ─────────────────────────────────────


class TestSupervisedRecoveryLoop:
    @pytest.mark.asyncio
    async def test_delegates_to_recovery_loop(self, mock_supabase):
        """Cas normal : délègue à recovery_loop et s'arrête sur SHUTDOWN."""
        from apps.worker.app.worker_loops import supervised_recovery_loop

        stopped = [False]

        def should_stop():
            return stopped[0]

        async def mock_recovery_loop(sb, stop_fn):
            stopped[0] = True

        with patch(
            "apps.worker.app.worker_loops.recovery_loop", side_effect=mock_recovery_loop
        ) as mock_loop:
            await supervised_recovery_loop(mock_supabase, should_stop)

        mock_loop.assert_called_once_with(mock_supabase, should_stop)

    @pytest.mark.asyncio
    async def test_restarts_after_crash(self, mock_supabase):
        """recovery_loop lève → log + sleep 10s + redémarre → stopped stoppe."""
        from apps.worker.app.worker_loops import supervised_recovery_loop

        stopped = [False]
        call_count = 0

        def should_stop():
            return stopped[0]

        async def flaky_recovery_loop(sb, stop_fn):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Crash!")
            stopped[0] = True

        sleep_calls = []

        async def mock_sleep(secs):
            sleep_calls.append(secs)

        with (
            patch(
                "apps.worker.app.worker_loops.recovery_loop",
                side_effect=flaky_recovery_loop,
            ),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            await supervised_recovery_loop(mock_supabase, should_stop)

        assert call_count == 2
        assert 10 in sleep_calls


# ─── supervised_gc_loop ───────────────────────────────────────────


class TestSupervisedGcLoop:
    @pytest.mark.asyncio
    async def test_delegates_to_gc_loop(self, mock_supabase):
        """Cas normal : délègue à gc_loop et s'arrête sur SHUTDOWN."""
        from apps.worker.app.worker_loops import supervised_gc_loop

        stopped = [False]

        def should_stop():
            return stopped[0]

        async def mock_gc_loop(sb, stop_fn):
            stopped[0] = True

        with patch(
            "apps.worker.app.worker_loops.gc_loop", side_effect=mock_gc_loop
        ) as mock_loop:
            await supervised_gc_loop(mock_supabase, should_stop)

        mock_loop.assert_called_once_with(mock_supabase, should_stop)

    @pytest.mark.asyncio
    async def test_restarts_after_crash(self, mock_supabase):
        """gc_loop lève → log + sleep 10s + redémarre → stopped stoppe."""
        from apps.worker.app.worker_loops import supervised_gc_loop

        stopped = [False]
        call_count = 0

        def should_stop():
            return stopped[0]

        async def flaky_gc_loop(sb, stop_fn):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("GC crash!")
            stopped[0] = True

        sleep_calls = []

        async def mock_sleep(secs):
            sleep_calls.append(secs)

        with (
            patch("apps.worker.app.worker_loops.gc_loop", side_effect=flaky_gc_loop),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            await supervised_gc_loop(mock_supabase, should_stop)

        assert call_count == 2
        assert 10 in sleep_calls


# ─── run_loop ─────────────────────────────────────────────────────


class TestRunLoop:
    """Tests pour run_loop — les supervised_*_loop sont mockées pour éviter les tâches de fond."""

    def _make_noop_coro(self):
        async def noop(*args, **kwargs):
            pass

        return noop

    @pytest.mark.asyncio
    async def test_complete_job_on_success(self, mock_supabase, mock_worker_imports):
        """Job trouvé + handler OK → complete_job appelé."""
        import apps.worker.app.main as worker_main

        job = {
            "id": "j10",
            "type": "index_source",
            "payload": {},
            "attempts": 0,
            "max_attempts": 3,
        }
        mock_worker_imports["app.services.indexing"].index_source = AsyncMock(
            return_value={"ok": True}
        )

        claim_results = [job]

        async def mock_claim(sb):
            if claim_results:
                return claim_results.pop(0)
            worker_main.SHUTDOWN = True
            return None

        original_shutdown = worker_main.SHUTDOWN
        worker_main.SHUTDOWN = False

        with (
            patch("apps.worker.app.main.load_config") as mock_cfg,
            patch("apps.worker.app.main.create_client", return_value=mock_supabase),
            patch(
                "apps.worker.app.main.supervised_recovery_loop", self._make_noop_coro()
            ),
            patch("apps.worker.app.main.supervised_gc_loop", self._make_noop_coro()),
            patch("apps.worker.app.main.claim_next_job", side_effect=mock_claim),
            patch(
                "apps.worker.app.main.complete_job", new_callable=AsyncMock
            ) as mock_complete,
            patch("apps.worker.app.main.fail_job", new_callable=AsyncMock) as mock_fail,
        ):
            mock_cfg.return_value = MagicMock(
                supabase_url="http://x", supabase_service_role_key="key"
            )
            await worker_main.run_loop()

        mock_complete.assert_called_once_with(mock_supabase, "j10", result={"ok": True})
        mock_fail.assert_not_called()
        worker_main.SHUTDOWN = original_shutdown

    @pytest.mark.asyncio
    async def test_fail_job_on_handler_error(self, mock_supabase, mock_worker_imports):
        """Handler lève → fail_job appelé avec le bon message."""
        import apps.worker.app.main as worker_main

        job = {
            "id": "j11",
            "type": "scan_workspace",
            "payload": {},
            "attempts": 1,
            "max_attempts": 3,
        }
        mock_worker_imports["app.agents.scanner"].run_scan = AsyncMock(
            side_effect=RuntimeError("Agent down")
        )

        claim_results = [job]

        async def mock_claim(sb):
            if claim_results:
                return claim_results.pop(0)
            worker_main.SHUTDOWN = True
            return None

        original_shutdown = worker_main.SHUTDOWN
        worker_main.SHUTDOWN = False

        with (
            patch("apps.worker.app.main.load_config") as mock_cfg,
            patch("apps.worker.app.main.create_client", return_value=mock_supabase),
            patch(
                "apps.worker.app.main.supervised_recovery_loop", self._make_noop_coro()
            ),
            patch("apps.worker.app.main.supervised_gc_loop", self._make_noop_coro()),
            patch("apps.worker.app.main.claim_next_job", side_effect=mock_claim),
            patch(
                "apps.worker.app.main.complete_job", new_callable=AsyncMock
            ) as mock_complete,
            patch("apps.worker.app.main.fail_job", new_callable=AsyncMock) as mock_fail,
        ):
            mock_cfg.return_value = MagicMock(
                supabase_url="http://x", supabase_service_role_key="key"
            )
            await worker_main.run_loop()

        mock_fail.assert_called_once()
        call_kwargs = mock_fail.call_args.kwargs
        assert "Agent down" in call_kwargs["error_message"]
        assert call_kwargs["attempts"] == 1
        assert call_kwargs["max_attempts"] == 3
        mock_complete.assert_not_called()
        worker_main.SHUTDOWN = original_shutdown

    @pytest.mark.asyncio
    async def test_sleeps_when_no_job(self, mock_supabase):
        """Aucun job → sleep(POLL_INTERVAL) puis SHUTDOWN."""
        import apps.worker.app.main as worker_main

        sleep_calls = []
        call_count = 0

        async def mock_claim(sb):
            return None

        async def mock_sleep(secs):
            nonlocal call_count
            sleep_calls.append(secs)
            call_count += 1
            worker_main.SHUTDOWN = True

        original_shutdown = worker_main.SHUTDOWN
        worker_main.SHUTDOWN = False

        with (
            patch("apps.worker.app.main.load_config") as mock_cfg,
            patch("apps.worker.app.main.create_client", return_value=mock_supabase),
            patch(
                "apps.worker.app.main.supervised_recovery_loop", self._make_noop_coro()
            ),
            patch("apps.worker.app.main.supervised_gc_loop", self._make_noop_coro()),
            patch("apps.worker.app.main.claim_next_job", side_effect=mock_claim),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            mock_cfg.return_value = MagicMock(
                supabase_url="http://x", supabase_service_role_key="key"
            )
            await worker_main.run_loop()

        assert worker_main.POLL_INTERVAL in sleep_calls
        worker_main.SHUTDOWN = original_shutdown

    @pytest.mark.asyncio
    async def test_outer_exception_sleeps_longer(self, mock_supabase):
        """Exception dans la boucle principale → sleep(POLL_INTERVAL * 5) puis SHUTDOWN."""
        import apps.worker.app.main as worker_main

        sleep_calls = []

        async def exploding_claim(sb):
            raise RuntimeError("DB gone")

        async def mock_sleep(secs):
            sleep_calls.append(secs)
            worker_main.SHUTDOWN = True

        original_shutdown = worker_main.SHUTDOWN
        worker_main.SHUTDOWN = False

        with (
            patch("apps.worker.app.main.load_config") as mock_cfg,
            patch("apps.worker.app.main.create_client", return_value=mock_supabase),
            patch(
                "apps.worker.app.main.supervised_recovery_loop", self._make_noop_coro()
            ),
            patch("apps.worker.app.main.supervised_gc_loop", self._make_noop_coro()),
            patch("apps.worker.app.main.claim_next_job", side_effect=exploding_claim),
            patch("asyncio.sleep", side_effect=mock_sleep),
        ):
            mock_cfg.return_value = MagicMock(
                supabase_url="http://x", supabase_service_role_key="key"
            )
            await worker_main.run_loop()

        assert worker_main.POLL_INTERVAL * 5 in sleep_calls
        worker_main.SHUTDOWN = original_shutdown
