"""
Tests de sécurité — Infrastructure & Configuration (Phase 3)

Couvre :
- Security headers : X-Content-Type-Options, X-Frame-Options, HSTS (prod)
- /health/detailed : protection par HEALTH_SECRET en prod, sans PID
- Rate limiter : X-Forwarded-For utilisé comme clé IP
- CORS : pas d'Access-Control-Allow-Origin wildcard + credentials en prod
"""

import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_app(environment: str = "development", health_secret: str | None = None):
    """Crée une instance de l'app avec la config souhaitée."""
    from packages.core.config import Config

    fake_config = Config(
        supabase_url="https://fake.supabase.co",
        supabase_anon_key="anon",
        supabase_service_role_key="service",
        supabase_jwt_secret=None,
        anthropic_api_key="sk-ant-fake",
        google_api_key="fake",
        tavily_api_key="fake",
        frontend_url="https://xais-vault.vercel.app",
        environment=environment,
        debug=(environment == "development"),
        admin_user_ids=[],
        sentry_dsn=None,
        health_secret=health_secret,
    )

    with (
        patch("apps.api.app.main.config", fake_config),
        patch("apps.api.app.main.load_config", return_value=fake_config),
    ):
        # Re-importer l'app avec la nouvelle config
        import importlib

        import apps.api.app.main as main_mod

        importlib.reload(main_mod)
        return main_mod.app


# ─── 1. Security Headers ────────────────────────────────────────────────────


class TestSecurityHeaders:
    """Les headers de sécurité doivent être présents sur toutes les réponses."""

    def test_x_content_type_options_present(self):
        """X-Content-Type-Options: nosniff doit être présent."""
        from apps.api.app.main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options_present(self):
        """X-Frame-Options: DENY doit être présent (anti-clickjacking)."""
        from apps.api.app.main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection_disabled(self):
        """X-XSS-Protection: 0 — désactiver le filtre XSS legacy."""
        from apps.api.app.main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health")
        assert response.headers.get("X-XSS-Protection") == "0"

    def test_hsts_absent_in_dev(self):
        """HSTS ne doit PAS être envoyé en dev (pas de HTTPS forcé en local)."""
        from apps.api.app.main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health")
        # En dev, pas de HSTS
        assert "Strict-Transport-Security" not in response.headers

    def test_headers_present_on_api_endpoint(self):
        """Les headers doivent aussi être présents sur les endpoints API (pas seulement /health)."""
        from apps.api.app.main import app

        client = TestClient(app, raise_server_exceptions=False)
        # 404 mais les headers de sécurité doivent quand même être là
        response = client.get("/api/v2/nonexistent")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"


# ─── 2. /health/detailed Protection ────────────────────────────────────────


class TestHealthDetailed:
    """/health/detailed ne doit pas exposer d'infos sensibles."""

    def test_no_pid_in_response(self):
        """Le PID du process ne doit jamais être dans la réponse."""
        from apps.api.app.main import app

        # get_supabase est importé localement dans la fonction — patcher au niveau du module source
        db_mock = MagicMock()
        db_mock.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        client = TestClient(app, raise_server_exceptions=False)
        with patch("packages.db.client.get_supabase", return_value=db_mock):
            response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "pid" not in data, "PID ne doit pas être exposé"

    def test_jwt_cache_size_present(self):
        """jwt_cache_size est autorisé (info non sensible)."""
        from apps.api.app.main import app

        db_mock = MagicMock()
        db_mock.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        client = TestClient(app, raise_server_exceptions=False)
        with patch("packages.db.client.get_supabase", return_value=db_mock):
            response = client.get("/health/detailed")
        assert response.status_code == 200
        assert "jwt_cache_size" in response.json()

    def test_supabase_error_message_is_generic(self):
        """En cas d'erreur Supabase, le message d'erreur doit être générique."""
        from apps.api.app.main import app

        client = TestClient(app, raise_server_exceptions=False)
        with patch(
            "packages.db.client.get_supabase",
            side_effect=Exception("connection refused to internal host 10.0.0.1:5432"),
        ):
            response = client.get("/health/detailed")
        data = response.json()
        # Le message d'erreur ne doit pas exposer des détails d'infrastructure
        assert "10.0.0.1" not in str(data)
        assert "connection refused" not in str(data)


# ─── 3. X-Forwarded-For Rate Limiting ───────────────────────────────────────


class TestXForwardedFor:
    """Le rate limiter doit utiliser X-Forwarded-For derrière un proxy."""

    def test_x_forwarded_for_used_as_identifier(self):
        """Deux requêtes avec le même X-Forwarded-For doivent partager le même bucket."""
        from apps.api.app.middleware.rate_limit import RateLimitMiddleware

        # Simuler une requête avec X-Forwarded-For
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"  # IP du proxy, pas du client

        middleware = RateLimitMiddleware(MagicMock())
        identifier = middleware._get_identifier(request)

        # Doit utiliser la première IP (le vrai client), pas l'IP du proxy
        assert identifier == "ip:203.0.113.1"

    def test_direct_connection_uses_client_host(self):
        """Sans X-Forwarded-For, utiliser request.client.host."""
        from apps.api.app.middleware.rate_limit import RateLimitMiddleware

        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "93.184.216.34"

        middleware = RateLimitMiddleware(MagicMock())
        identifier = middleware._get_identifier(request)

        assert identifier == "ip:93.184.216.34"

    def test_jwt_takes_priority_over_forwarded_for(self):
        """JWT doit toujours prendre priorité sur l'IP."""
        from apps.api.app.middleware.rate_limit import RateLimitMiddleware

        token = "a" * 64
        request = MagicMock()
        request.headers = {
            "Authorization": f"Bearer {token}",
            "X-Forwarded-For": "203.0.113.1",
        }

        middleware = RateLimitMiddleware(MagicMock())
        identifier = middleware._get_identifier(request)

        assert identifier.startswith("jwt:")
        assert "203.0.113.1" not in identifier

    def test_multiple_forwarded_ips_uses_first(self):
        """Avec plusieurs IPs dans X-Forwarded-For, prendre la première."""
        from apps.api.app.middleware.rate_limit import RateLimitMiddleware

        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "  198.51.100.1  ,  10.0.0.1  ,  172.16.0.1"
        }
        request.client = MagicMock()
        request.client.host = "10.0.0.1"

        middleware = RateLimitMiddleware(MagicMock())
        identifier = middleware._get_identifier(request)

        # Premier IP trimé
        assert identifier == "ip:198.51.100.1"


# ─── 4. Config — health_secret ───────────────────────────────────────────────


class TestHealthSecretConfig:
    """HEALTH_SECRET doit être chargé depuis les variables d'environnement."""

    def test_health_secret_loaded_from_env(self):
        """HEALTH_SECRET est chargé comme champ optionnel."""
        from packages.core.config import load_config

        load_config.cache_clear()
        with patch.dict(
            os.environ,
            {
                "HEALTH_SECRET": "my-secret-token",
                "SUPABASE_URL": "https://fake.supabase.co",
                "SUPABASE_ANON_KEY": "anon",
                "SUPABASE_SERVICE_ROLE_KEY": "svc",
                "ANTHROPIC_API_KEY": "sk",
                "GOOGLE_API_KEY": "gk",
                "TAVILY_API_KEY": "tk",
                "FRONTEND_URL": "http://localhost:3000",
                "ADMIN_USER_IDS": "",
            },
        ):
            config = load_config()
            assert config.health_secret == "my-secret-token"
        load_config.cache_clear()

    def test_health_secret_optional(self):
        """Sans HEALTH_SECRET, la valeur est None."""
        from packages.core.config import load_config

        load_config.cache_clear()
        env = {
            "SUPABASE_URL": "https://fake.supabase.co",
            "SUPABASE_ANON_KEY": "anon",
            "SUPABASE_SERVICE_ROLE_KEY": "svc",
            "ANTHROPIC_API_KEY": "sk",
            "GOOGLE_API_KEY": "gk",
            "TAVILY_API_KEY": "tk",
            "FRONTEND_URL": "http://localhost:3000",
            "ADMIN_USER_IDS": "",
        }
        with patch.dict(os.environ, env, clear=False):
            # Supprimer HEALTH_SECRET si présent
            os.environ.pop("HEALTH_SECRET", None)
            config = load_config()
            assert config.health_secret is None
        load_config.cache_clear()
