"""
Factory for LLM and Embedding providers.
Singleton pattern — one instance per provider, lazily initialized.

Usage:
    from packages.llm.factory import get_llm, get_embedder

    llm = get_llm()
    embedder = get_embedder()
"""

import logging
import threading

from packages.core.config import load_config

from .claude import ClaudeProvider
from .gemini_embeddings import GeminiEmbeddingProvider

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_llm_instance: ClaudeProvider | None = None
_embedder_instance: GeminiEmbeddingProvider | None = None


def get_llm() -> ClaudeProvider:
    """Get the singleton Claude LLM provider."""
    global _llm_instance
    if _llm_instance is None:
        with _lock:
            if _llm_instance is None:  # Double-checked locking
                config = load_config()
                _llm_instance = ClaudeProvider(api_key=config.anthropic_api_key)
                logger.info("Initialized Claude LLM provider")
    return _llm_instance


def get_embedder() -> GeminiEmbeddingProvider:
    """Get the singleton Gemini Embedding 2 provider."""
    global _embedder_instance
    if _embedder_instance is None:
        with _lock:
            if _embedder_instance is None:  # Double-checked locking
                config = load_config()
                _embedder_instance = GeminiEmbeddingProvider(api_key=config.google_api_key)
                logger.info("Initialized Gemini Embedding 2 provider")
    return _embedder_instance
