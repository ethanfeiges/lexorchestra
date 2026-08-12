"""Model client protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ModelClient(Protocol):
    """Async LLM client interface."""

    async def complete(self, system: str, user: str) -> str:
        """Return raw model response text."""
