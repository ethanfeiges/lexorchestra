"""Tests for docProcessing.prompt."""

from docProcessing.models import Clause, SoTCandidate, SoTBundle
from docProcessing.prompt import (
    format_candidates_for_prompt,
    get_candidate_by_label,
    signed_contract_candidate,
)


def _make_bundle() -> SoTBundle:
    long_text = "A" * 600
    clauses = [
        Clause(id="c-001", text="Short clause text.", start_offset=0, end_offset=18),
        Clause(id="c-002", text=long_text, start_offset=18, end_offset=618),
    ]
    signed = SoTCandidate(label="signed_contract", valid=True, clauses=clauses)
    decoy = SoTCandidate(
        label="outdated_wrong_terms",
        valid=False,
        clauses=clauses,
        corruption="altered_text",
    )
    return SoTBundle(
        document_id="test",
        source_path="test.txt",
        canonical=clauses,
        candidates=[signed, decoy],
    )


def test_output_contains_requested_labels():
    bundle = _make_bundle()
    text = format_candidates_for_prompt(
        bundle.candidates, labels=["signed_contract", "outdated_wrong_terms"]
    )
    assert "[signed_contract]" in text
    assert "[outdated_wrong_terms]" in text
    assert "Document versions (cite from signed_contract only):" in text


def test_unlabeled_aliases_in_prompt():
    bundle = _make_bundle()
    text = format_candidates_for_prompt(
        bundle.candidates,
        labels=["signed_contract", "outdated_wrong_terms"],
        header="Document versions (labels are arbitrary):",
        label_aliases={
            "signed_contract": "version_2",
            "outdated_wrong_terms": "version_1",
        },
    )
    assert "[version_1]" in text
    assert "[version_2]" in text
    assert "signed_contract" not in text
    assert "labels are arbitrary" in text


def test_signed_contract_label_present():
    bundle = _make_bundle()
    text = format_candidates_for_prompt(bundle.candidates)
    assert "[signed_contract] c-001:" in text


def test_truncation_for_long_clauses():
    long_text = "A" * 13_000
    clauses = [
        Clause(id="c-001", text=long_text, start_offset=0, end_offset=len(long_text)),
    ]
    signed = SoTCandidate(label="signed_contract", valid=True, clauses=clauses)
    bundle = SoTBundle(
        document_id="test",
        source_path="test.txt",
        canonical=clauses,
        candidates=[signed],
    )
    text = format_candidates_for_prompt(bundle.candidates)
    assert "..." in text
    assert long_text not in text


def test_get_candidate_by_label():
    bundle = _make_bundle()
    assert get_candidate_by_label(bundle, "signed_contract") is not None
    assert get_candidate_by_label(bundle, "missing") is None


def test_signed_contract_candidate():
    bundle = _make_bundle()
    candidate = signed_contract_candidate(bundle)
    assert candidate.valid is True
