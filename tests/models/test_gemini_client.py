"""Tests for Gemini client adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.gemini_client import GeminiClient, resolve_gemini_api_key


@pytest.mark.asyncio
async def test_gemini_complete_returns_json_text(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = GeminiClient(model="gemini-2.5-pro")

    mock_response = MagicMock()
    mock_response.text = '{"claims": []}'

    mock_aio = MagicMock()
    mock_aio.models.generate_content = AsyncMock(return_value=mock_response)

    mock_genai_client = MagicMock()
    mock_genai_client.aio = mock_aio

    with patch("google.genai.Client", return_value=mock_genai_client):
        result = await client.complete("system prompt", "user prompt")

    assert result == '{"claims": []}'
    mock_aio.models.generate_content.assert_awaited_once()
    call_kwargs = mock_aio.models.generate_content.await_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-pro"
    assert call_kwargs["contents"] == "user prompt"


@pytest.mark.asyncio
async def test_gemini_complete_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    client = GeminiClient()
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        await client.complete("system", "user")


def test_resolve_gemini_api_key_empty(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert resolve_gemini_api_key() == ""
