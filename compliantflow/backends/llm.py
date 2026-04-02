"""LLM backend abstractions for CompliantFlow semantic checks.

Provides a Protocol-based abstraction over LLM providers so that
PolicyEngine is not hard-wired to any specific SDK.
"""

import os
from typing import Optional
from typing import runtime_checkable, Protocol


@runtime_checkable
class LLMBackend(Protocol):
    """Protocol for LLM backends used by PolicyEngine."""

    def generate(self, prompt: str) -> str:
        """Send *prompt* to the LLM and return the response text."""
        ...


class GeminiBackend:
    """LLM backend that delegates to Google Gemini via the google-genai SDK."""

    _MODEL = "gemini-2.5-flash"
    _CONFIG = {"temperature": 0}  # deterministic output for reproducible CI results

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def generate(self, prompt: str) -> str:
        from google import genai
        client = genai.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self._MODEL,
            contents=prompt,
            config=self._CONFIG,
        )
        return response.text.strip()


class OllamaBackend:
    """LLM backend that calls an Ollama-compatible REST API.

    Configuration is read from environment variables:
      - ``COMPLIANTFLOW_OLLAMA_URL``  — base URL (default: http://localhost:11434)
      - ``COMPLIANTFLOW_OLLAMA_MODEL`` — model name (default: llama3)
    """

    def __init__(self, url: Optional[str] = None, model: Optional[str] = None) -> None:
        self._url = (url or os.environ.get("COMPLIANTFLOW_OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self._model = model or os.environ.get("COMPLIANTFLOW_OLLAMA_MODEL", "llama3")

    def generate(self, prompt: str) -> str:
        import requests
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }
        response = requests.post(f"{self._url}/api/generate", json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["response"].strip()


def get_default_backend() -> Optional[LLMBackend]:
    """Return the best available LLM backend, or None if none is configured.

    Resolution order:
      1. ``GEMINI_API_KEY`` → :class:`GeminiBackend`
      2. ``COMPLIANTFLOW_OLLAMA_URL`` → :class:`OllamaBackend`
      3. None
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return GeminiBackend(api_key=api_key)

    ollama_url = os.environ.get("COMPLIANTFLOW_OLLAMA_URL")
    if ollama_url:
        return OllamaBackend(url=ollama_url)

    return None
