"""
Tests unitaires pour ClaudeProvider — generate_with_tools, _extract_json, _to_anthropic_tools.

Tous les appels API sont mockés via unittest.mock — aucun call réseau.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.llm.claude import ClaudeProvider, _extract_json, _to_anthropic_tools
from packages.llm.types import ToolCall, ToolResult

# ─── Helpers ─────────────────────────────────────────────────────


def _make_response(
    content_blocks: list,
    stop_reason: str = "end_turn",
    input_tokens: int = 10,
    output_tokens: int = 20,
) -> MagicMock:
    """Construit un mock de réponse Anthropic."""
    response = MagicMock()
    response.content = content_blocks
    response.stop_reason = stop_reason
    response.usage.input_tokens = input_tokens
    response.usage.output_tokens = output_tokens
    return response


def _text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _tool_use_block(id: str, name: str, input: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.id = id
    block.name = name
    block.input = input
    return block


@pytest.fixture
def provider():
    """ClaudeProvider avec client Anthropic mocké."""
    with patch("packages.llm.claude.anthropic.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value = mock_client
        p = ClaudeProvider(api_key="test-key")
        p._client = mock_client
        yield p


# ─── _extract_json ────────────────────────────────────────────────


class TestExtractJson:
    def test_plain_json_returned_as_is(self):
        text = '{"key": "value"}'
        assert _extract_json(text) == text

    def test_json_fence_stripped(self):
        text = '```json\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == '{"key": "value"}'

    def test_generic_fence_stripped(self):
        text = '```\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == '{"key": "value"}'

    def test_invalid_json_returns_raw_text(self):
        text = "voici une réponse non-JSON"
        result = _extract_json(text)
        assert result == text

    def test_empty_string_returns_empty(self):
        result = _extract_json("")
        assert result == ""

    def test_json_with_whitespace(self):
        text = '  { "a": 1 }  '
        result = _extract_json(text)
        assert json.loads(result) == {"a": 1}


# ─── _to_anthropic_tools ─────────────────────────────────────────


class TestToAnthropicTools:
    def test_full_tool_converted(self):
        tools = [
            {
                "name": "search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            }
        ]
        result = _to_anthropic_tools(tools)
        assert len(result) == 1
        assert result[0]["name"] == "search"
        assert result[0]["description"] == "Search the web"
        assert result[0]["input_schema"]["properties"]["query"]["type"] == "string"

    def test_missing_description_defaults_to_empty(self):
        tools = [{"name": "noop", "parameters": {"type": "object", "properties": {}}}]
        result = _to_anthropic_tools(tools)
        assert result[0]["description"] == ""

    def test_missing_parameters_defaults_to_empty_schema(self):
        tools = [{"name": "noop", "description": "does nothing"}]
        result = _to_anthropic_tools(tools)
        assert result[0]["input_schema"] == {"type": "object", "properties": {}}

    def test_empty_list(self):
        assert _to_anthropic_tools([]) == []

    def test_multiple_tools(self):
        tools = [{"name": "a"}, {"name": "b"}]
        result = _to_anthropic_tools(tools)
        assert [t["name"] for t in result] == ["a", "b"]


# ─── generate_with_tools ─────────────────────────────────────────


class TestGenerateWithTools:
    @pytest.fixture
    def tools(self):
        return [{"name": "search", "description": "Recherche web"}]

    @pytest.mark.asyncio
    async def test_first_call_builds_single_user_message(self, provider, tools):
        """Premier appel : un seul message user."""
        response = _make_response(
            [_text_block("Voici ma réponse")], stop_reason="end_turn"
        )
        provider._client.messages.create = AsyncMock(return_value=response)

        result = await provider.generate_with_tools("Recherche Python", tools)

        call_kwargs = provider._client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "Recherche Python"}

    @pytest.mark.asyncio
    async def test_continuation_builds_user_assistant_user(self, provider, tools):
        """Continuation : séquence user → assistant → user (obligatoire Anthropic)."""
        response = _make_response(
            [_text_block("Résultat final")], stop_reason="end_turn"
        )
        provider._client.messages.create = AsyncMock(return_value=response)

        previous_tool_calls = [
            ToolCall(id="tc_1", name="search", arguments={"query": "Python"})
        ]
        tool_results = [
            ToolResult(tool_call_id="tc_1", content="Python est un langage")
        ]

        await provider.generate_with_tools(
            "Recherche Python",
            tools,
            tool_results=tool_results,
            previous_tool_calls=previous_tool_calls,
        )

        call_kwargs = provider._client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

        # Vérifier le contenu du message assistant
        assert messages[1]["content"][0]["type"] == "tool_use"
        assert messages[1]["content"][0]["id"] == "tc_1"
        assert messages[1]["content"][0]["name"] == "search"

        # Vérifier les tool_results
        assert messages[2]["content"][0]["type"] == "tool_result"
        assert messages[2]["content"][0]["tool_use_id"] == "tc_1"
        assert messages[2]["content"][0]["content"] == "Python est un langage"

    @pytest.mark.asyncio
    async def test_extracts_tool_calls_from_response(self, provider, tools):
        """Extrait les ToolCall depuis les blocs tool_use."""
        response = _make_response(
            [_tool_use_block("tc_42", "search", {"query": "FastAPI"})],
            stop_reason="tool_use",
        )
        provider._client.messages.create = AsyncMock(return_value=response)

        result = await provider.generate_with_tools("Recherche FastAPI", tools)

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].id == "tc_42"
        assert result.tool_calls[0].name == "search"
        assert result.tool_calls[0].arguments == {"query": "FastAPI"}
        assert result.content is None

    @pytest.mark.asyncio
    async def test_text_only_response(self, provider, tools):
        """Réponse texte uniquement — tool_calls vide."""
        response = _make_response(
            [_text_block("Je réponds sans tool")], stop_reason="end_turn"
        )
        provider._client.messages.create = AsyncMock(return_value=response)

        result = await provider.generate_with_tools("Dis bonjour", tools)

        assert result.content == "Je réponds sans tool"
        assert result.tool_calls == []

    @pytest.mark.asyncio
    async def test_stop_reason_propagated(self, provider, tools):
        """stop_reason est propagé dans LLMToolResponse."""
        response = _make_response(
            [_tool_use_block("tc_1", "search", {})],
            stop_reason="tool_use",
        )
        provider._client.messages.create = AsyncMock(return_value=response)

        result = await provider.generate_with_tools("Test", tools)

        assert result.stop_reason == "tool_use"

    @pytest.mark.asyncio
    async def test_raises_without_previous_calls_when_tool_results_provided(
        self, provider, tools
    ):
        """tool_results sans previous_tool_calls → ValueError."""
        tool_results = [ToolResult(tool_call_id="tc_1", content="résultat")]

        with pytest.raises(ValueError, match="previous_tool_calls est requis"):
            await provider.generate_with_tools(
                "Prompt",
                tools,
                tool_results=tool_results,
                # previous_tool_calls intentionnellement absent
            )

    @pytest.mark.asyncio
    async def test_non_dict_input_defaults_to_empty_dict(self, provider, tools):
        """Si block.input n'est pas un dict → arguments = {}."""
        block = _tool_use_block("tc_1", "search", None)
        block.input = "string_invalide"

        response = _make_response([block], stop_reason="tool_use")
        provider._client.messages.create = AsyncMock(return_value=response)

        result = await provider.generate_with_tools("Test", tools)

        assert result.tool_calls[0].arguments == {}

    @pytest.mark.asyncio
    async def test_system_prompt_included_in_kwargs(self, provider, tools):
        """system fourni → présent dans les kwargs de l'appel API."""
        response = _make_response([_text_block("Réponse")], stop_reason="end_turn")
        provider._client.messages.create = AsyncMock(return_value=response)

        await provider.generate_with_tools("Prompt", tools, system="Tu es un expert PE")

        call_kwargs = provider._client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "Tu es un expert PE"


# ─── generate ─────────────────────────────────────────────────────


class TestGenerate:
    @pytest.mark.asyncio
    async def test_nominal_returns_llm_response(self, provider):
        response = _make_response(
            [_text_block("Bonjour le monde")], input_tokens=5, output_tokens=3
        )
        provider._client.messages.create = AsyncMock(return_value=response)

        result = await provider.generate("Dis bonjour")

        assert result.content == "Bonjour le monde"
        assert result.usage.input_tokens == 5
        assert result.usage.output_tokens == 3

    @pytest.mark.asyncio
    async def test_empty_content_returns_empty_string(self, provider):
        response = _make_response([])
        provider._client.messages.create = AsyncMock(return_value=response)

        result = await provider.generate("Prompt")

        assert result.content == ""

    @pytest.mark.asyncio
    async def test_json_mode_strips_fences(self, provider):
        response = _make_response([_text_block('```json\n{"ok": true}\n```')])
        provider._client.messages.create = AsyncMock(return_value=response)

        result = await provider.generate("JSON please", json_mode=True)

        import json

        assert json.loads(result.content) == {"ok": True}

    @pytest.mark.asyncio
    async def test_system_prompt_forwarded(self, provider):
        response = _make_response([_text_block("ok")])
        provider._client.messages.create = AsyncMock(return_value=response)

        await provider.generate("Prompt", system="Contexte système")

        call_kwargs = provider._client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "Contexte système"

    @pytest.mark.asyncio
    async def test_no_system_omitted_from_kwargs(self, provider):
        response = _make_response([_text_block("ok")])
        provider._client.messages.create = AsyncMock(return_value=response)

        await provider.generate("Prompt")

        call_kwargs = provider._client.messages.create.call_args.kwargs
        assert "system" not in call_kwargs

    @pytest.mark.asyncio
    async def test_custom_model_forwarded(self, provider):
        response = _make_response([_text_block("ok")])
        provider._client.messages.create = AsyncMock(return_value=response)

        await provider.generate("Prompt", model="claude-haiku-4-5-20251001")

        call_kwargs = provider._client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"

    @pytest.mark.asyncio
    async def test_high_max_tokens_uses_stream(self, provider):
        """max_tokens > seuil → utilise le streaming interne."""
        final_msg = MagicMock()
        final_msg.usage.input_tokens = 100
        final_msg.usage.output_tokens = 500

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.text_stream = _aiter_helper("Rapport ", "complet")
        mock_stream.get_final_message = AsyncMock(return_value=final_msg)
        provider._client.messages.stream = MagicMock(return_value=mock_stream)

        result = await provider.generate("Génère un DD Report", max_tokens=16384)

        assert result.content == "Rapport complet"
        assert result.usage.input_tokens == 100
        assert result.usage.output_tokens == 500
        provider._client.messages.stream.assert_called_once()
        provider._client.messages.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_low_max_tokens_uses_create(self, provider):
        """max_tokens <= seuil → utilise create classique."""
        response = _make_response([_text_block("Court")])
        provider._client.messages.create = AsyncMock(return_value=response)

        result = await provider.generate("Prompt court", max_tokens=4096)

        assert result.content == "Court"
        provider._client.messages.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stream_generate_with_json_mode(self, provider):
        """Streaming interne + json_mode → le JSON est nettoyé."""
        final_msg = MagicMock()
        final_msg.usage.input_tokens = 10
        final_msg.usage.output_tokens = 20

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.text_stream = _aiter_helper('```json\n{"ok":', " true}\n```")
        mock_stream.get_final_message = AsyncMock(return_value=final_msg)
        provider._client.messages.stream = MagicMock(return_value=mock_stream)

        result = await provider.generate("JSON", max_tokens=16384, json_mode=True)

        assert json.loads(result.content) == {"ok": True}


# ─── stream ───────────────────────────────────────────────────────


async def _aiter(*items):
    """Helper — async generator depuis une liste d'items."""
    for item in items:
        yield item


async def _aiter_helper(*items):
    """Helper — async generator (utilisé hors TestStream)."""
    for item in items:
        yield item


class TestStream:
    @pytest.mark.asyncio
    async def test_yields_text_chunks_then_final(self, provider):
        final_msg = MagicMock()
        final_msg.usage.input_tokens = 10
        final_msg.usage.output_tokens = 5

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.text_stream = _aiter("Bonjour", " monde")
        mock_stream.get_final_message = AsyncMock(return_value=final_msg)
        provider._client.messages.stream = MagicMock(return_value=mock_stream)

        chunks = []
        async for chunk in provider.stream("Test"):
            chunks.append(chunk)

        # 2 text chunks + 1 final
        assert len(chunks) == 3
        assert chunks[0].content == "Bonjour"
        assert chunks[1].content == " monde"
        assert chunks[2].is_final is True
        assert chunks[2].usage.input_tokens == 10

    @pytest.mark.asyncio
    async def test_empty_stream_only_final_chunk(self, provider):
        final_msg = MagicMock()
        final_msg.usage.input_tokens = 5
        final_msg.usage.output_tokens = 0

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.text_stream = _aiter()  # Aucun chunk
        mock_stream.get_final_message = AsyncMock(return_value=final_msg)
        provider._client.messages.stream = MagicMock(return_value=mock_stream)

        chunks = []
        async for chunk in provider.stream("Prompt"):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0].is_final is True

    @pytest.mark.asyncio
    async def test_system_forwarded_in_stream(self, provider):
        final_msg = MagicMock()
        final_msg.usage.input_tokens = 1
        final_msg.usage.output_tokens = 1

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.text_stream = _aiter("ok")
        mock_stream.get_final_message = AsyncMock(return_value=final_msg)
        provider._client.messages.stream = MagicMock(return_value=mock_stream)

        async for _ in provider.stream("Test", system="Contexte"):
            pass

        call_kwargs = provider._client.messages.stream.call_args.kwargs
        assert call_kwargs["system"] == "Contexte"
