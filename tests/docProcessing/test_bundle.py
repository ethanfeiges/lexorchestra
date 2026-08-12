"""Tests for docProcessing.bundle."""

from pathlib import Path

from docProcessing.bundle import build_bundle
from docProcessing.io import build_bundle_from_file
from docProcessing.parser import parse_document

FIXTURES = Path(__file__).resolve().parents[2] / "legalDocs" / "contracts"
PRIMARY_MSA = FIXTURES / "public" / "edgar_edgemode_inc_ex10.1.txt"


def _canonical():
    return parse_document(PRIMARY_MSA)


def test_bundle_has_one_valid_and_four_invalid():
    bundle = build_bundle(
        _canonical(),
        "edgar_edgemode_inc_ex10.1",
        str(PRIMARY_MSA),
    )
    assert len(bundle.candidates) == 5
    valid = [c for c in bundle.candidates if c.valid]
    assert len(valid) == 1
    assert valid[0].label == "signed_contract"


def test_missing_clause_has_fewer_clauses():
    bundle = build_bundle(
        _canonical(), "edgar_edgemode_inc_ex10.1", str(PRIMARY_MSA), seed=42
    )
    decoy = next(c for c in bundle.candidates if c.corruption == "missing_clause")
    assert len(decoy.clauses) < len(bundle.canonical)


def test_altered_text_same_ids_different_text():
    bundle = build_bundle(
        _canonical(), "edgar_edgemode_inc_ex10.1", str(PRIMARY_MSA), seed=42
    )
    decoy = next(c for c in bundle.candidates if c.corruption == "altered_text")
    assert [c.id for c in decoy.clauses] == [c.id for c in bundle.canonical]
    assert any(d.text != c.text for d, c in zip(decoy.clauses, bundle.canonical))


def test_extra_clause_has_more_clauses():
    bundle = build_bundle(
        _canonical(), "edgar_edgemode_inc_ex10.1", str(PRIMARY_MSA), seed=42
    )
    decoy = next(c for c in bundle.candidates if c.corruption == "extra_clause")
    assert len(decoy.clauses) > len(bundle.canonical)


def test_reordered_same_texts_different_mapping():
    bundle = build_bundle(
        _canonical(), "edgar_edgemode_inc_ex10.1", str(PRIMARY_MSA), seed=42
    )
    decoy = next(c for c in bundle.candidates if c.corruption == "reordered")
    canonical_texts = sorted(c.text for c in bundle.canonical)
    decoy_texts = sorted(c.text for c in decoy.clauses)
    assert canonical_texts == decoy_texts
    id_to_text_canonical = {c.id: c.text for c in bundle.canonical}
    id_to_text_decoy = {c.id: c.text for c in decoy.clauses}
    assert id_to_text_canonical != id_to_text_decoy


def test_same_seed_produces_identical_bundle():
    args = (_canonical(), "edgar_edgemode_inc_ex10.1", str(PRIMARY_MSA), 42)
    b1 = build_bundle(*args)
    b2 = build_bundle(*args)
    assert b1.model_dump() == b2.model_dump()


def test_build_bundle_from_file(primary_msa_path: Path):
    bundle = build_bundle_from_file(primary_msa_path, seed=42)
    assert bundle.document_id == "edgar_edgemode_inc_ex10.1"
    assert len(bundle.canonical) >= 3
