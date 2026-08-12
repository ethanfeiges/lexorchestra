"""Tests for grounding verifier."""

import json
from pathlib import Path

import pytest

from grounding.verifier import verify_claim, verify_claims
from orchestrator.models import Claim
from docProcessing.io import build_bundle_from_file
from docProcessing.store import SoTStore

FIXTURES = Path(__file__).resolve().parents[2] / "legalDocs" / "contracts"
PRIMARY = FIXTURES / "public" / "edgar_edgemode_inc_ex10.1.txt"


@pytest.fixture
def bundle():
    return build_bundle_from_file(PRIMARY, seed=42)


@pytest.fixture
def store(bundle):
    return SoTStore(bundle.canonical, bundle.document_id)


def test_grounded_canonical_claim(store):
    clause = store.get("c-005")
    claim = Claim(
        statement="Fee indexation",
        clause_id="c-005",
        quote="three per cent ( 3 % )",
        sot_label="signed_contract",
    )
    result = verify_claim(claim, store, model="test", task="extract")
    assert result.status == "grounded"
    assert result.reason is None


def test_ungrounded_missing_clause(store):
    claim = Claim(
        statement="Fake",
        clause_id="c-999",
        quote="nothing",
    )
    result = verify_claim(claim, store, model="test", task="extract")
    assert result.status == "ungrounded"
    assert result.reason == "missing_clause"


def test_ungrounded_text_mismatch(store):
    clause = store.get("c-005")
    assert clause is not None
    claim = Claim(
        statement="Wrong quote",
        clause_id="c-005",
        quote="completely unrelated text that does not appear",
    )
    result = verify_claim(claim, store, model="test", task="extract")
    assert result.status == "ungrounded"
    assert result.reason == "text_mismatch"


def test_decoy_quote_not_grounded(bundle, store):
    decoy = next(c for c in bundle.candidates if c.corruption == "altered_text")
    decoy_store = SoTStore(decoy.clauses, bundle.document_id)
    canonical = store.get("c-005")
    decoy_clause = decoy_store.get("c-005")
    assert canonical is not None
    assert decoy_clause is not None
    if decoy_clause.text == canonical.text:
        pytest.skip("No text change at c-005 for this seed")

    claim = Claim(
        statement="From decoy",
        clause_id="c-005",
        quote=decoy_clause.text[:80],
    )
    result = verify_claim(
        claim, store, model="test", task="extract", bundle=bundle
    )
    assert result.status == "ungrounded"
    assert result.decoy_match == "outdated_wrong_terms"


def test_sot_label_decoy_flags_metric(bundle, store):
    claim = Claim(
        statement="Explicit decoy label",
        clause_id="c-005",
        quote="three per cent",
        sot_label="outdated_wrong_terms",
    )
    result = verify_claim(
        claim, store, model="test", task="extract", bundle=bundle
    )
    assert result.decoy_match == "outdated_wrong_terms"


def test_verify_claims_batch(store):
    claims = [
        Claim(statement="a", clause_id="c-005", quote="three per cent"),
        Claim(statement="b", clause_id="c-999", quote="x"),
    ]
    results = verify_claims(claims, store, model="m", task="t")
    assert len(results) == 2
    assert results[0].status == "grounded"
    assert results[1].status == "ungrounded"
