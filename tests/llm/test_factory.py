"""
Tests for packages/llm/factory.py

Vérifie le pattern singleton (double-checked locking) pour get_llm() et get_embedder().
Les providers réels ne sont jamais instanciés — tout est mocké.
"""

from unittest.mock import MagicMock, patch

import packages.llm.factory as factory_module


def _reset_singletons():
    """Réinitialise les singletons entre les tests."""
    factory_module._llm_instance = None
    factory_module._embedder_instance = None


# ─── get_llm ───────────────────────────────────────────────────


class TestGetLlm:
    def setup_method(self):
        _reset_singletons()

    def test_returns_claude_provider(self):
        """get_llm() retourne un ClaudeProvider initialisé avec l'API key."""
        mock_config = MagicMock()
        mock_config.anthropic_api_key = "sk-test-key"
        mock_provider = MagicMock()

        with (
            patch("packages.llm.factory.load_config", return_value=mock_config),
            patch(
                "packages.llm.factory.ClaudeProvider", return_value=mock_provider
            ) as mock_cls,
        ):
            result = factory_module.get_llm()

        mock_cls.assert_called_once_with(api_key="sk-test-key")
        assert result is mock_provider

    def test_singleton_same_instance(self):
        """Deux appels consécutifs retournent le même objet."""
        mock_config = MagicMock()
        mock_config.anthropic_api_key = "sk-test"
        mock_provider = MagicMock()

        with (
            patch("packages.llm.factory.load_config", return_value=mock_config),
            patch("packages.llm.factory.ClaudeProvider", return_value=mock_provider),
        ):
            first = factory_module.get_llm()
            second = factory_module.get_llm()

        assert first is second

    def test_config_loaded_only_once(self):
        """load_config() appelé une seule fois, pas à chaque appel."""
        mock_config = MagicMock()
        mock_config.anthropic_api_key = "sk-test"

        with (
            patch(
                "packages.llm.factory.load_config", return_value=mock_config
            ) as mock_load,
            patch("packages.llm.factory.ClaudeProvider", return_value=MagicMock()),
        ):
            factory_module.get_llm()
            factory_module.get_llm()
            factory_module.get_llm()

        mock_load.assert_called_once()

    def test_existing_instance_returned_directly(self):
        """Si l'instance existe déjà, load_config n'est jamais appelé."""
        factory_module._llm_instance = MagicMock()

        with patch("packages.llm.factory.load_config") as mock_load:
            result = factory_module.get_llm()

        mock_load.assert_not_called()
        assert result is factory_module._llm_instance


# ─── get_embedder ──────────────────────────────────────────────


class TestGetEmbedder:
    def setup_method(self):
        _reset_singletons()

    def test_returns_gemini_provider(self):
        """get_embedder() retourne un GeminiEmbeddingProvider initialisé."""
        mock_config = MagicMock()
        mock_config.google_api_key = "google-test-key"
        mock_provider = MagicMock()

        with (
            patch("packages.llm.factory.load_config", return_value=mock_config),
            patch(
                "packages.llm.factory.GeminiEmbeddingProvider",
                return_value=mock_provider,
            ) as mock_cls,
        ):
            result = factory_module.get_embedder()

        mock_cls.assert_called_once_with(api_key="google-test-key")
        assert result is mock_provider

    def test_singleton_same_instance(self):
        """Deux appels consécutifs retournent le même objet."""
        mock_config = MagicMock()
        mock_config.google_api_key = "google-key"
        mock_provider = MagicMock()

        with (
            patch("packages.llm.factory.load_config", return_value=mock_config),
            patch(
                "packages.llm.factory.GeminiEmbeddingProvider",
                return_value=mock_provider,
            ),
        ):
            first = factory_module.get_embedder()
            second = factory_module.get_embedder()

        assert first is second

    def test_llm_and_embedder_are_independent(self):
        """get_llm() et get_embedder() sont des singletons indépendants."""
        mock_config = MagicMock()
        mock_config.anthropic_api_key = "sk-test"
        mock_config.google_api_key = "google-key"

        with (
            patch("packages.llm.factory.load_config", return_value=mock_config),
            patch("packages.llm.factory.ClaudeProvider", return_value=MagicMock()),
            patch(
                "packages.llm.factory.GeminiEmbeddingProvider", return_value=MagicMock()
            ),
        ):
            llm = factory_module.get_llm()
            embedder = factory_module.get_embedder()

        assert llm is not embedder
