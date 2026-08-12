"""Read-only store over canonical clauses."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from docProcessing.models import Clause


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


class SoTStore:
    """Read-only wrapper over canonical clauses with lookup and quote matching."""

    def __init__(self, clauses: list[Clause], document_id: str) -> None:
        self._clauses = {c.id: c for c in clauses}
        self._document_id = document_id

    @property
    def document_id(self) -> str:
        return self._document_id

    def get_all(self) -> list[Clause]:
        return list(self._clauses.values())

    def get(self, clause_id: str) -> Clause | None:
        return self._clauses.get(clause_id)

    def contains(self, clause_id: str) -> bool:
        return clause_id in self._clauses

    def quote_matches(
        self, clause_id: str, quote: str, threshold: float = 0.85
    ) -> bool:
        clause = self.get(clause_id)
        if clause is None:
            return False

        norm_quote = _normalize_whitespace(quote)
        norm_clause = _normalize_whitespace(clause.text)

        if not norm_quote:
            return False

        if norm_quote in norm_clause:
            return True

        ratio = SequenceMatcher(None, norm_quote, norm_clause).ratio()
        return ratio >= threshold
