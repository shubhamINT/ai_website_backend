"""
Shared async LLM formatting utilities for parsing snapshots into structured text.
"""

import logging
from typing import TypeVar, Type

from pydantic import BaseModel

from src.core.config import settings
from src.services.llm.client import get_openai_client

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


async def llm_parse(
    snapshot: dict,
    system_prompt: str,
    response_model: Type[T],
) -> T | None:
    """
    Ask the LLM to parse a snapshot into a typed Pydantic model.

    Returns None if OpenAI is not configured or the call fails,
    so callers can fall back gracefully.
    """
    if not settings.OPENAI_API_KEY:
        return None

    try:
        client = get_openai_client()
        response = await client.beta.chat.completions.parse(
            model=settings.EMAIL_SUMMARY_MODEL,
            temperature=0.2,
            response_format=response_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(snapshot)},
            ],
        )
        return response.choices[0].message.parsed
    except Exception as exc:
        logger.error("LLM formatting failed: %s", exc)
        return None


async def llm_text(
    snapshot: dict,
    system_prompt: str,
) -> str | None:
    """
    Ask the LLM to produce a plain-text string from a snapshot.

    Returns None if OpenAI is not configured or the call fails.
    """
    if not settings.OPENAI_API_KEY:
        return None

    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.EMAIL_SUMMARY_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(snapshot)},
            ],
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception as exc:
        logger.error("LLM text formatting failed: %s", exc)
        return None
