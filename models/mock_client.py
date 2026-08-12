"""Mock LLM clients for tests."""

from __future__ import annotations

from collections.abc import Callable


class StaticModelClient:
    """Returns a fixed response regardless of prompt."""

    def __init__(self, response: str) -> None:
        self._response = response

    async def complete(self, system: str, user: str) -> str:
        return self._response


class MockModelClient:
    """Routes responses by task type detected in the user prompt."""

    def __init__(
        self,
        extract_response: str,
        playbook_response: str,
    ) -> None:
        self._extract = extract_response
        self._playbook = playbook_response

    async def complete(self, system: str, user: str) -> str:
        if "Task (playbook)" in user:
            return self._playbook
        return self._extract


class CallableModelClient:
    """Delegates to a callable for dynamic responses."""

    def __init__(self, fn: Callable[[str, str], str]) -> None:
        self._fn = fn

    async def complete(self, system: str, user: str) -> str:
        return self._fn(system, user)
