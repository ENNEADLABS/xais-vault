"""Tests pour packages/llm/token_counter.py"""

from packages.llm.token_counter import count_tokens, truncate_to_tokens


def test_count_tokens_basic():
    assert count_tokens("Hello world!") == 3  # 12 chars / 4


def test_count_tokens_empty():
    assert count_tokens("") == 0


def test_truncate_short_text():
    """Texte court retourné tel quel."""
    text = "Bonjour le monde."
    assert truncate_to_tokens(text, 100) == text


def test_truncate_sentence_boundary():
    """Coupe en fin de phrase."""
    text = "Première phrase. Deuxième phrase. Troisième phrase qui est longue."
    result = truncate_to_tokens(text, 10)  # 40 chars max
    assert result.endswith(".")
    assert len(result) <= 40


def test_truncate_no_boundary():
    """Coupe brute si pas de délimiteur dans les 70% finaux."""
    text = "a" * 200
    result = truncate_to_tokens(text, 10)  # 40 chars max
    assert len(result) <= 40
