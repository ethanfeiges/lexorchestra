"""Verify agent claims against canonical SoT only."""

from __future__ import annotations

from orchestrator.models import Claim, VerifiedClaim
from docProcessing.models import SoTBundle
from docProcessing.store import SoTStore

from grounding.decoy_detect import find_decoy_match


def verify_claim(
    claim: Claim,
    store: SoTStore,
    *,
    model: str,
    task: str,
    bundle: SoTBundle | None = None,
) -> VerifiedClaim:
    """Verify one claim against canonical store."""
    decoy_match: str | None = None

    if not store.contains(claim.clause_id):
        status = "ungrounded"
        reason = "missing_clause"
    elif not store.quote_matches(claim.clause_id, claim.quote):
        status = "ungrounded"
        reason = "text_mismatch"
        if bundle is not None:
            decoy_match = find_decoy_match(
                claim.clause_id, claim.quote, bundle, store
            )
    else:
        status = "grounded"
        reason = None

    if decoy_match is None and bundle is not None and status == "ungrounded":
        decoy_match = find_decoy_match(claim.clause_id, claim.quote, bundle, store)

    if claim.sot_label is not None and claim.sot_label != "signed_contract":
        if decoy_match is None:
            decoy_match = claim.sot_label

    return VerifiedClaim(
        claim=claim,
        status=status,
        reason=reason,
        model=model,
        task=task,
        decoy_match=decoy_match,
    )


def verify_claims(
    claims: list[Claim],
    store: SoTStore,
    *,
    model: str,
    task: str,
    bundle: SoTBundle | None = None,
) -> list[VerifiedClaim]:
    """Verify a batch of claims."""
    return [
        verify_claim(claim, store, model=model, task=task, bundle=bundle)
        for claim in claims
    ]
