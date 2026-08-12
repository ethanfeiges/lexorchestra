"""Detect whether a claim quote matches a decoy candidate."""

from __future__ import annotations

import re

from docProcessing.models import SoTCandidate, SoTBundle
from docProcessing.store import SoTStore


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def find_decoy_match(
    clause_id: str,
    quote: str,
    bundle: SoTBundle,
    store: SoTStore,
) -> str | None:
    """Return decoy label if quote matches a decoy but not canonical."""
    if store.quote_matches(clause_id, quote):
        return None

    norm_quote = _normalize(quote)
    if not norm_quote:
        return None

    for candidate in bundle.candidates:
        if candidate.valid:
            continue
        decoy_store = SoTStore(candidate.clauses, bundle.document_id)
        if decoy_store.quote_matches(clause_id, quote):
            return candidate.label

    return None
