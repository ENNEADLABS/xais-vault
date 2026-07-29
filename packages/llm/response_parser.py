"""Safe JSON parsing with Pydantic — handles raw JSON and markdown codeblocks."""

import logging
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def parse_llm_json(content: str, model: type[T], fallback: T) -> T:
    """Parse LLM JSON output into a Pydantic model.

    1. Essaie model_validate_json direct
    2. Si échec, tente d'extraire le JSON d'un codeblock markdown
    3. Si échec total, retourne le fallback
    """
    # Tenter directement
    try:
        return model.model_validate_json(content)
    except (ValidationError, ValueError):
        pass

    # Tenter d'extraire du markdown codeblock
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", content, re.DOTALL)
    if match:
        try:
            return model.model_validate_json(match.group(1))
        except (ValidationError, ValueError):
            pass

    logger.warning("Failed to parse LLM response as %s, using fallback", model.__name__)
    return fallback
