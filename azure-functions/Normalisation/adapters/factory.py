from .base import BaseProviderAdapter
from .gemini import GeminiAdapter
from .groq import GroqAdapter


def get_adapter(provider: str) -> BaseProviderAdapter:

    if not provider:
        return BaseProviderAdapter()

    provider = provider.lower()

    if provider in ["google", "gemini", "vertex"]:
        return GeminiAdapter()

    if provider in ["groq", "openai", "azure", "together", "fireworks", "deepinfra"]:
        return GroqAdapter()

    return BaseProviderAdapter()