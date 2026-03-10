from openai import AsyncOpenAI

from src.core.config import settings


def get_openai_client() -> AsyncOpenAI:
    """Get a singleton AsyncOpenAI client."""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=8.0)
