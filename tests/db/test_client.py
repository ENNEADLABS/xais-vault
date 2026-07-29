"""
Tests pour packages/db/client.py

- safe_get_one, safe_get_list, require_one
- get_supabase (erreur si env manquantes)
- paginate
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

# ─── safe_get_one ────────────────────────────────────────────────────────────


def test_safe_get_one_returns_first_row():
    """Retourne le premier row quand data non vide."""
    from packages.db.client import safe_get_one

    result = MagicMock()
    result.data = [{"id": 1}, {"id": 2}]
    assert safe_get_one(result) == {"id": 1}


def test_safe_get_one_returns_none_on_empty():
    """Retourne None quand data est vide."""
    from packages.db.client import safe_get_one

    result = MagicMock()
    result.data = []
    assert safe_get_one(result) is None


def test_safe_get_one_returns_none_on_none():
    """Retourne None quand data est None."""
    from packages.db.client import safe_get_one

    result = MagicMock()
    result.data = None
    assert safe_get_one(result) is None


# ─── safe_get_list ───────────────────────────────────────────────────────────


def test_safe_get_list_returns_data():
    """Retourne la liste quand data non vide."""
    from packages.db.client import safe_get_list

    result = MagicMock()
    result.data = [{"id": 1}]
    assert safe_get_list(result) == [{"id": 1}]


def test_safe_get_list_returns_empty_on_none():
    """Retourne [] quand data est None."""
    from packages.db.client import safe_get_list

    result = MagicMock()
    result.data = None
    assert safe_get_list(result) == []


# ─── require_one ─────────────────────────────────────────────────────────────


def test_require_one_returns_row():
    """Retourne le row quand trouvé."""
    from packages.db.client import require_one

    result = MagicMock()
    result.data = [{"id": 1, "name": "Test"}]
    assert require_one(result, "Workspace") == {"id": 1, "name": "Test"}


def test_require_one_raises_404_on_empty():
    """Lève HTTPException 404 quand aucun résultat."""
    from packages.db.client import require_one

    result = MagicMock()
    result.data = []
    with pytest.raises(HTTPException) as exc_info:
        require_one(result, "Workspace")
    assert exc_info.value.status_code == 404
    assert "Workspace not found" in exc_info.value.detail


# ─── get_supabase — env manquantes ───────────────────────────────────────────


def test_get_supabase_raises_without_env(monkeypatch):
    """get_supabase() lève RuntimeError sans SUPABASE_URL."""
    import packages.db.client as module

    # Reset le lru_cache
    module.get_supabase.cache_clear()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        module.get_supabase()

    # Re-clear pour ne pas polluer
    module.get_supabase.cache_clear()


# ─── paginate ────────────────────────────────────────────────────────────────


def test_paginate_page_1():
    """Page 1 → range(0, per_page-1)."""
    from packages.db.client import paginate

    query = MagicMock()
    query.range.return_value = query
    paginate(query, page=1, per_page=20)
    query.range.assert_called_once_with(0, 19)


def test_paginate_page_3():
    """Page 3, per_page=10 → range(20, 29)."""
    from packages.db.client import paginate

    query = MagicMock()
    query.range.return_value = query
    paginate(query, page=3, per_page=10)
    query.range.assert_called_once_with(20, 29)
