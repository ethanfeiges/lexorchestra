"""Detect cross-document citation in portfolio runs."""

from __future__ import annotations

from orchestrator.models import Claim
from docProcessing.store import SoTStore


def find_cross_document_match(
    claim: Claim,
    stores: dict[str, SoTStore],
    expected_document_id: str,
) -> str | None:
    """Return other document_id if claim anchors on the wrong document."""
    if claim.document_id and claim.document_id != expected_document_id:
        return claim.document_id

    norm_quote = claim.quote.strip()
    if not norm_quote or not claim.clause_id:
        return None

    expected = stores.get(expected_document_id)
    if expected is not None and expected.quote_matches(claim.clause_id, claim.quote):
        return None

    for doc_id, store in stores.items():
        if doc_id == expected_document_id:
            continue
        if store.quote_matches(claim.clause_id, claim.quote):
            return doc_id
    return None
