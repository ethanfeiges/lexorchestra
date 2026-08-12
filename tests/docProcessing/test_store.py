"""Tests for docProcessing.store."""

from docProcessing.models import Clause
from docProcessing.store import SoTStore


def _sample_clauses() -> list[Clause]:
    return [
        Clause(
            id="c-001",
            text="Limitation of Liability. Aggregate liability shall not exceed $1,000,000.",
            start_offset=0,
            end_offset=70,
        ),
        Clause(
            id="c-002",
            text="Payment Terms. Invoices are due within thirty (30) days of receipt.",
            start_offset=70,
            end_offset=130,
        ),
    ]


def test_get_and_contains():
    store = SoTStore(_sample_clauses(), "doc-1")
    assert store.contains("c-001")
    assert not store.contains("c-999")
    assert store.get("c-001") is not None
    assert store.get("c-999") is None


def test_get_all():
    store = SoTStore(_sample_clauses(), "doc-1")
    assert len(store.get_all()) == 2


def test_quote_matches_exact_substring():
    store = SoTStore(_sample_clauses(), "doc-1")
    assert store.quote_matches("c-001", "Aggregate liability shall not exceed")
    assert not store.quote_matches("c-001", "payment within sixty days")


def test_quote_matches_fuzzy_paraphrase():
    store = SoTStore(_sample_clauses(), "doc-1")
    quote = "Limitation of Liability Aggregate liability shall not exceed one million dollars"
    assert store.quote_matches("c-001", quote, threshold=0.5)
