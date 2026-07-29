"""
Tests pour packages/llm/response_parser.py

- JSON direct valide
- JSON dans un codeblock markdown
- Codeblock markdown avec JSON invalide → fallback
- Contenu non parsable → fallback
"""

from pydantic import BaseModel

from packages.llm.response_parser import parse_llm_json


class SampleModel(BaseModel):
    score: int
    label: str


FALLBACK = SampleModel(score=0, label="unknown")


# ─── JSON direct ─────────────────────────────────────────────────────────────


def test_parse_valid_json():
    """JSON direct → parse OK."""
    result = parse_llm_json('{"score": 42, "label": "good"}', SampleModel, FALLBACK)
    assert result.score == 42
    assert result.label == "good"


def test_parse_invalid_json_returns_fallback():
    """Contenu non-JSON, pas de codeblock → fallback."""
    result = parse_llm_json("This is not JSON at all", SampleModel, FALLBACK)
    assert result is FALLBACK


# ─── Markdown codeblock ──────────────────────────────────────────────────────


def test_parse_json_in_codeblock():
    """JSON dans un codeblock ```json → parse OK."""
    content = '```json\n{"score": 99, "label": "excellent"}\n```'
    result = parse_llm_json(content, SampleModel, FALLBACK)
    assert result.score == 99
    assert result.label == "excellent"


def test_parse_json_in_codeblock_no_lang():
    """JSON dans un codeblock ``` sans spécifier json."""
    content = '```\n{"score": 5, "label": "low"}\n```'
    result = parse_llm_json(content, SampleModel, FALLBACK)
    assert result.score == 5


def test_parse_codeblock_invalid_json_returns_fallback():
    """Codeblock markdown avec JSON invalide pour le modèle → fallback."""
    content = '```json\n{"wrong_field": true}\n```'
    result = parse_llm_json(content, SampleModel, FALLBACK)
    assert result is FALLBACK


def test_parse_codeblock_malformed_json_returns_fallback():
    """Codeblock markdown avec JSON cassé → fallback."""
    content = "```json\n{not valid json}\n```"
    result = parse_llm_json(content, SampleModel, FALLBACK)
    assert result is FALLBACK


# ─── Edge cases ──────────────────────────────────────────────────────────────


def test_parse_empty_string_returns_fallback():
    """Chaîne vide → fallback."""
    result = parse_llm_json("", SampleModel, FALLBACK)
    assert result is FALLBACK


def test_parse_partial_json_returns_fallback():
    """JSON tronqué sans codeblock → fallback."""
    result = parse_llm_json('{"score": 1, "label":', SampleModel, FALLBACK)
    assert result is FALLBACK
