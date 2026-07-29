"""
Compteur de tokens — estimation rapide pour le budget contexte RAG.

Estimation 4 chars/token (conservatrice). La marge d'erreur ~10%
est acceptable pour le budget contexte.
"""

CHARS_PER_TOKEN = 4


def count_tokens(text: str) -> int:
    """Estime le nombre de tokens dans un texte."""
    return len(text) // CHARS_PER_TOKEN


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Tronque un texte à max_tokens, en coupant en fin de phrase.

    Cherche le dernier point ou saut de ligne avant la limite.
    """
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    for delimiter in [". ", ".\n", "\n\n", "\n"]:
        last = truncated.rfind(delimiter)
        if last > max_chars * 0.7:
            return truncated[: last + len(delimiter)].rstrip()

    return truncated.rstrip()
