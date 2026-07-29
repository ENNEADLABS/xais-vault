"""
Tests pour apps/api/app/services/chat_history.py

Vérifie la persistance des coûts de summarization dans usage_logs.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from apps.api.app.services.chat_history import _persist_usage


def _make_usage():
    return SimpleNamespace(
        input_tokens=850,
        output_tokens=320,
        cost_usd=0.00125,
        model="claude-sonnet-4-20250514",
    )


def _make_db(session_data=None, deal_data=None):
    """Crée un mock DB avec chaîne table().select().eq().execute()."""
    db = MagicMock()

    # Simuler les appels chaînés pour chat_sessions et workspaces
    call_count = {"n": 0}
    responses = [session_data, deal_data]

    def mock_table(name):
        table_mock = MagicMock()

        if name == "usage_logs":
            return table_mock

        result_mock = MagicMock()
        result_mock.data = (
            [responses[call_count["n"]]] if responses[call_count["n"]] else []
        )
        table_mock.select.return_value.eq.return_value.execute.return_value = (
            result_mock
        )
        call_count["n"] += 1
        return table_mock

    db.table = mock_table
    return db


class TestPersistUsage:
    def test_insere_dans_usage_logs(self):
        """Un appel réussi insère un row dans usage_logs."""
        session_data = {"workspace_id": "workspace-123"}
        deal_data = {"organization_id": "org-456"}

        # Simuler chat_sessions → workspace_id
        session_result = MagicMock()
        session_result.data = [session_data]

        # Simuler workspaces → organization_id
        workspace_result = MagicMock()
        workspace_result.data = [deal_data]

        # Mock stable pour usage_logs (même ref à chaque appel)
        usage_logs_mock = MagicMock()
        call_idx = {"n": 0}
        results = [session_result, workspace_result]

        def mock_table(name):
            if name == "usage_logs":
                return usage_logs_mock
            mock = MagicMock()
            mock.select.return_value.eq.return_value.execute.return_value = results[
                call_idx["n"]
            ]
            call_idx["n"] += 1
            return mock

        db = MagicMock()
        db.table = mock_table
        usage = _make_usage()

        _persist_usage(db, "session-1", usage)

        # Vérifier que usage_logs a reçu l'insert
        usage_logs_mock.insert.assert_called_once()
        inserted = usage_logs_mock.insert.call_args[0][0]
        assert inserted["organization_id"] == "org-456"
        assert inserted["workspace_id"] == "workspace-123"
        assert inserted["operation"] == "summarization"
        assert inserted["input_tokens"] == 850
        assert inserted["output_tokens"] == 320
        assert inserted["cost_usd"] == 0.00125

    def test_ne_plante_pas_si_session_introuvable(self):
        """Si la session n'existe pas, pas d'insert ni d'erreur."""
        db = MagicMock()
        empty_result = MagicMock()
        empty_result.data = []
        db.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_result

        _persist_usage(db, "session-inexistante", _make_usage())
        # Pas d'exception = OK

    def test_ne_plante_pas_si_deal_introuvable(self):
        """Si le workspace n'existe pas, pas d'insert ni d'erreur."""
        db = MagicMock()

        call_idx = {"n": 0}

        def mock_table(name):
            mock = MagicMock()
            if name == "usage_logs":
                return mock
            result = MagicMock()
            if call_idx["n"] == 0:
                result.data = [{"workspace_id": "workspace-123"}]
            else:
                result.data = []
            mock.select.return_value.eq.return_value.execute.return_value = result
            call_idx["n"] += 1
            return mock

        db.table = mock_table
        _persist_usage(db, "session-1", _make_usage())

    def test_ne_plante_pas_sur_exception_db(self):
        """Si l'insert échoue, on log un warning mais pas d'exception."""
        db = MagicMock()
        db.table.side_effect = Exception("DB down")

        # Ne doit pas lever d'exception
        _persist_usage(db, "session-1", _make_usage())
