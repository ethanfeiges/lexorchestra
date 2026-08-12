"""Tests for docProcessing.parser."""

from pathlib import Path

import pytest

from docProcessing.parser import normalize_text, parse_document, parse_text

FIXTURES = Path(__file__).resolve().parents[2] / "legalDocs" / "contracts"
PUBLIC_DIR = FIXTURES / "public"
PRIMARY_MSA = PUBLIC_DIR / "edgar_edgemode_inc_ex10.1.txt"


def test_parse_real_msa_has_sequential_ids(primary_msa_path: Path):
    text = primary_msa_path.read_text(encoding="utf-8")
    clauses = parse_text(text)
    assert len(clauses) >= 3
    assert [c.id for c in clauses] == [f"c-{i:03d}" for i in range(1, len(clauses) + 1)]


def test_offsets_match_text_slices(primary_msa_path: Path):
    text = primary_msa_path.read_text(encoding="utf-8")
    normalized = normalize_text(text)
    clauses = parse_text(text)
    for clause in clauses:
        assert normalized[clause.start_offset : clause.end_offset] == clause.text


def test_heading_based_split():
    text = """Preamble paragraph that is long enough to stand alone as its own clause here.

1. First Section. This section contains important definitions and terms for the agreement.

2. Second Section. This section describes the term and duration of the agreement between parties.
"""
    clauses = parse_text(text)
    assert len(clauses) >= 2
    assert any("First Section" in c.text for c in clauses)
    assert any("Second Section" in c.text for c in clauses)


def test_paragraph_fallback_when_no_headings():
    text = """This is the first paragraph of a document without any numbered headings at all.

This is the second paragraph and it also has enough characters to qualify as a clause.

This is the third paragraph with sufficient length to avoid being merged away entirely.
"""
    clauses = parse_text(text)
    assert len(clauses) >= 3
    assert all(len(c.text) >= 40 for c in clauses)


def test_parse_document_from_real_msa(primary_msa_path: Path):
    clauses = parse_document(primary_msa_path)
    assert len(clauses) >= 3
    assert "Master Services Agreement" in primary_msa_path.read_text(encoding="utf-8")
