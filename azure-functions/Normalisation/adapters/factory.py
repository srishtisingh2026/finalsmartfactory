from .base import BaseProviderAdapter
from .gemini import GeminiAdapter
from .groq import GroqAdapter


def get_adapter(provider: str) -> BaseProviderAdapter:

    if provider == "google":
        return GeminiAdapter()

    if provider in ["groq", "openai"]:
        return GroqAdapter()

    return BaseProviderAdapter()