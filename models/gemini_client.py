"""Google Gemini API client adapter."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable

from models.base import ModelClient

DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
MAX_RETRIES = 5
RETRY_BASE_SEC = 5.0

# Chime has 184 clauses (~285k chars) and routinely exceeds free-tier TPM limits.
LIVE_DOCUMENTS_EXCLUDE = frozenset({"edgar_chime_financial_inc_ex10.1"})


def resolve_gemini_api_key() -> str:
    """Return Gemini API key from GEMINI_API_KEY or GOOGLE_API_KEY."""
    return (
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY", "").strip()
    )


def build_gemini_client_factory(
    default_model: str = DEFAULT_GEMINI_MODEL,
) -> Callable[[str], ModelClient]:
    """Return a client_factory compatible with run_benchmark_case."""

    def factory(model: str) -> ModelClient:
        return GeminiClient(model=model or default_model)

    return factory


class GeminiClient:
    """Async Gemini client via google-genai."""

    def __init__(self, model: str = DEFAULT_GEMINI_MODEL) -> None:
        self.model = model
        self._api_key = resolve_gemini_api_key()
        self._client: object | None = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def complete(self, system: str, user: str) -> str:
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY not set")

        try:
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "Install google-genai: pip install google-genai"
            ) from exc

        client = self._get_client()
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.aio.models.generate_content(
                    model=self.model,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                    ),
                )
                return response.text or ""
            except Exception as exc:
                last_exc = exc
                msg = str(exc).lower()
                if (
                    "429" in msg
                    or "503" in msg
                    or "resource_exhausted" in msg
                    or "quota" in msg
                    or "unavailable" in msg
                ):
                    delay = RETRY_BASE_SEC * (attempt + 1)
                    await asyncio.sleep(delay)
                    continue
                raise
        raise RuntimeError(f"Gemini API failed after {MAX_RETRIES} retries") from last_exc
