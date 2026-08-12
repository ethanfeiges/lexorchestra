"""Tests for document type registry."""

from benchmark.document_types import (
    DOCUMENT_TYPES,
    document_type_for_id,
    primary_fixtures,
)


def test_primary_fixtures_one_per_type():
    primaries = primary_fixtures()
    assert len(primaries) == len(DOCUMENT_TYPES)
    assert len(set(primaries)) == len(primaries)


def test_document_type_for_edgemode():
    assert document_type_for_id("edgar_edgemode_inc_ex10.1") == "msa"


def test_document_type_for_amd():
    assert document_type_for_id("edgar_amd_ex10.79") == "software_license"
