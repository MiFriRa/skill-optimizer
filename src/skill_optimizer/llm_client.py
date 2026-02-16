"""
LLM Client abstraction.

Provides a configurable, multi-provider LLM system.
Supports Gemini and Anthropic out of the box; new providers
can be added by subclassing LLMClient.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Send a prompt and return the model's text response."""
        ...

    @abstractmethod
    def generate_sync(self, prompt: str) -> str:
        """Synchronous version of generate()."""
        ...


class GeminiClient(LLMClient):
    """Google Gemini API client using google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key required. Pass api_key= or set GEMINI_API_KEY in .env"
            )

        from google import genai
        self._client = genai.Client(api_key=self.api_key)

    async def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text

    def generate_sync(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text


class AnthropicClient(LLMClient):
    """Anthropic Claude API client."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Pass api_key= or set ANTHROPIC_API_KEY in .env"
            )

    async def generate(self, prompt: str) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self.api_key)
        response = await client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def generate_sync(self, prompt: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


# ── Factory ──────────────────────────────────────────────────────

_PROVIDERS = {
    "gemini": GeminiClient,
    "anthropic": AnthropicClient,
}


def create_client(
    provider: str = "gemini",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMClient:
    """Create an LLM client for the given provider.

    Args:
        provider: "gemini" or "anthropic"
        api_key: Optional API key (falls back to .env / env vars)
        model: Optional model override (uses provider default if None)
    """
    cls = _PROVIDERS.get(provider.lower())
    if cls is None:
        available = ", ".join(_PROVIDERS.keys())
        raise ValueError(f"Unknown provider '{provider}'. Available: {available}")

    kwargs: dict = {}
    if api_key:
        kwargs["api_key"] = api_key
    if model:
        kwargs["model"] = model
    return cls(**kwargs)
