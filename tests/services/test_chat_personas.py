"""Tests pour les personas système du chat RAG."""

from apps.api.app.services.prompts.chat_personas import (
    DD_PERSONA,
    DEFAULT_PERSONA,
    GENERAL_PERSONA,
    PERSONAS,
    get_persona,
)


def test_default_persona_is_general():
    assert DEFAULT_PERSONA == "general"


def test_get_persona_returns_general_for_none():
    assert get_persona(None) == GENERAL_PERSONA


def test_get_persona_returns_general_for_empty_string():
    assert get_persona("") == GENERAL_PERSONA


def test_get_persona_returns_general_for_unknown_name():
    assert get_persona("nonexistent") == GENERAL_PERSONA


def test_get_persona_returns_dd_when_requested():
    assert get_persona("dd") == DD_PERSONA


def test_general_persona_does_not_mention_due_diligence():
    assert "due diligence" not in GENERAL_PERSONA.lower()
    assert "private equity" not in GENERAL_PERSONA.lower()
    assert "venture capital" not in GENERAL_PERSONA.lower()


def test_general_persona_keeps_citation_format():
    # Le pattern [SOURCE:source_id:page:section:quote] doit être préservé
    # en parité avec DD pour ne pas casser le parser de citations.
    assert "[SOURCE:source_id:page:section:quote]" in GENERAL_PERSONA


def test_dd_persona_mentions_due_diligence():
    assert "due diligence" in DD_PERSONA.lower()


def test_dd_persona_keeps_citation_format():
    assert "[SOURCE:source_id:page:section:quote]" in DD_PERSONA


def test_personas_dict_contains_known_keys():
    assert set(PERSONAS.keys()) == {"general", "dd"}
