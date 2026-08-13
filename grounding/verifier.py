"""Verify agent claims against canonical SoT only."""

from __future__ import annotations

from orchestrator.models import Claim, VerifiedClaim
from docProcessing.models import SoTBundle
from docProcessing.store import SoTStore

from grounding.cross_document_detect import find_cross_document_match
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


def verify_portfolio_claim(
    claim: Claim,
    store: SoTStore,
    *,
    expected_document_id: str,
    model: str,
    task: str,
    bundle: SoTBundle | None = None,
    all_stores: dict[str, SoTStore] | None = None,
) -> VerifiedClaim:
    """Verify a portfolio claim against the assigned document's canonical store."""
    routed = claim.model_copy(
        update={"document_id": claim.document_id or expected_document_id}
    )
    result = verify_claim(
        routed,
        store,
        model=model,
        task=task,
        bundle=bundle,
    )
    cross_match: str | None = None
    if all_stores is not None:
        cross_match = find_cross_document_match(
            routed,
            all_stores,
            expected_document_id,
        )
    if cross_match is not None and result.status == "grounded":
        result = VerifiedClaim(
            claim=routed,
            status="ungrounded",
            reason="cross_document",
            model=model,
            task=task,
            decoy_match=result.decoy_match,
            cross_document_match=cross_match,
            expected_document_id=expected_document_id,
        )
    else:
        result = result.model_copy(
            update={
                "cross_document_match": cross_match,
                "expected_document_id": expected_document_id,
            }
        )
    return result


def verify_portfolio_claims(
    claims: list[Claim],
    store: SoTStore,
    *,
    expected_document_id: str,
    model: str,
    task: str,
    bundle: SoTBundle | None = None,
    all_stores: dict[str, SoTStore] | None = None,
) -> list[VerifiedClaim]:
    """Verify portfolio claims for one assigned document."""
    return [
        verify_portfolio_claim(
            claim,
            store,
            expected_document_id=expected_document_id,
            model=model,
            task=task,
            bundle=bundle,
            all_stores=all_stores,
        )
        for claim in claims
    ]


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
