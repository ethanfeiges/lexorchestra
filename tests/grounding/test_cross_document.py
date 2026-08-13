"""Cross-document citation detection tests."""

from docProcessing.io import build_bundle_from_file
from docProcessing.store import SoTStore
from grounding.cross_document_detect import find_cross_document_match
from orchestrator.models import Claim

FIXTURES = (
    __import__("pathlib").Path(__file__).resolve().parents[2]
    / "legalDocs"
    / "contracts"
    / "public"
)
DOC_A = FIXTURES / "edgar_edgemode_inc_ex10.1.txt"
DOC_B = FIXTURES / "edgar_amd_ex10.79.txt"


def test_find_cross_document_match_by_explicit_document_id():
    claim = Claim(
        statement="wrong routing",
        clause_id="c-001",
        quote="anything",
        document_id="edgar_amd_ex10.79",
    )
    stores = {
        "edgar_edgemode_inc_ex10.1": SoTStore(
            build_bundle_from_file(DOC_A, seed=42).canonical,
            "edgar_edgemode_inc_ex10.1",
        ),
        "edgar_amd_ex10.79": SoTStore(
            build_bundle_from_file(DOC_B, seed=42).canonical,
            "edgar_amd_ex10.79",
        ),
    }
    match = find_cross_document_match(
        claim,
        stores,
        expected_document_id="edgar_edgemode_inc_ex10.1",
    )
    assert match == "edgar_amd_ex10.79"


def test_find_cross_document_match_by_quote_in_other_store():
    bundle_a = build_bundle_from_file(DOC_A, seed=42)
    bundle_b = build_bundle_from_file(DOC_B, seed=42)
    stores = {
        "edgar_edgemode_inc_ex10.1": SoTStore(bundle_a.canonical, "edgar_edgemode_inc_ex10.1"),
        "edgar_amd_ex10.79": SoTStore(bundle_b.canonical, "edgar_amd_ex10.79"),
    }
    other_clause = bundle_b.canonical[0]
    claim = Claim(
        statement="quoted other doc",
        clause_id=other_clause.id,
        quote=other_clause.text[:80],
        document_id="edgar_edgemode_inc_ex10.1",
    )
    match = find_cross_document_match(
        claim,
        stores,
        expected_document_id="edgar_edgemode_inc_ex10.1",
    )
    assert match == "edgar_amd_ex10.79"
